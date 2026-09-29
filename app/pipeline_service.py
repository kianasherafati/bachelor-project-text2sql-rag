"""One orchestration boundary. No model loading or database access on import."""
import re
from time import perf_counter

from app.contracts import PipelineResponse
from app.adapters import DemoExecutor, DemoGenerator, DemoSchemaProvider, project_validator


def validation_reason(errors):
    # Never forward parser excerpts or arbitrary backend errors to the browser.
    messages = []
    for error in errors:
        if error.startswith("Forbidden SQL operation") or error == "Only SELECT queries are allowed.":
            messages.append("Only read-only SELECT queries are allowed.")
        elif error.startswith("Unknown table"):
            messages.append("The query references an unrecognized table or alias.")
        elif error.startswith("Unknown column"):
            messages.append("The query references an unrecognized column.")
        elif error == "Exactly one SQL statement is allowed.":
            messages.append(error)
        else:
            messages.append("The generated SQL could not be safely validated.")
    return " ".join(dict.fromkeys(messages)) or "The query did not pass validation."


class PipelineService:
    def __init__(self, schema, generator, executor, validator=project_validator, *, mode="demo"):
        if mode not in ("demo", "live"):
            raise ValueError("Unknown application mode")
        if any(getattr(adapter, "is_demo", None) is not (mode == "demo")
               for adapter in (schema, generator, executor)):
            raise ValueError("Demo and live adapters cannot be mixed")
        self.schema, self.generator, self.executor = schema, generator, executor
        self.validator, self.mode = validator, mode

    def run(self, question, on_progress=None):
        response = PipelineResponse(question=question.strip(), mode=self.mode)
        started = perf_counter()
        stage = "retrieval"

        def operation(name, callback):
            nonlocal stage
            stage = name
            response.steps[name] = "running"
            if on_progress:
                on_progress(dict(response.steps))
            tick = perf_counter()
            try:
                value = callback()
            finally:
                response.timings[name] = max(0.0, perf_counter() - tick)
            response.steps[name] = "success"
            return value

        def skip_after(name):
            reached = False
            for step in response.steps:
                if reached and response.steps[step] == "waiting":
                    response.steps[step] = "skipped"
                if step == name:
                    reached = True

        try:
            if not response.question or len(response.question) > 2000:
                response.status = "INPUT_ERROR"
                response.error = "Enter an English reporting question of 1–2,000 characters."
                return response
            candidates = operation("retrieval", lambda: self.schema.retrieve(response.question))
            response.retrieved_tables = list(operation("reranking", lambda: self.schema.rerank(response.question, candidates)))
            # Preserve the provider's final ranking exactly; never rerank in the UI.
            if len(response.retrieved_tables) > 10:
                raise ValueError("Provider must return its final Top10 selection")
            output = operation("generation", lambda: self.generator.generate(response.question, response.retrieved_tables))
            sql = output.strip()
            fenced = re.fullmatch(r"```(?:sql|tsql)?\s*\n?(.*?)\n?```", sql, re.I | re.S)
            if fenced:
                sql = fenced.group(1).strip()
            if sql.upper() in ("INSUFFICIENT_SCHEMA", "I DO NOT KNOW"):
                response.status = response.generation_status = "INSUFFICIENT_SCHEMA"
                response.steps["generation"] = "abstained"
                response.validation_status = "skipped"
                response.execution_status = "skipped"
                skip_after("generation")
                return response
            response.generated_sql = sql
            response.generation_status = "success"
            validation = operation("validation", lambda: self.validator(sql))
            if not validation["valid"]:
                response.status = "VALIDATION_REJECTED"
                response.validation_status = "rejected"
                response.validation_message = validation_reason(validation.get("errors", []))
                response.steps["validation"] = "rejected"
                response.execution_status = "skipped"
                skip_after("validation")
                return response
            response.validation_status = "valid"
            response.validation_message = "Passed the project SQL validator."
            response.generated_sql = validation["cleaned_sql"]
            result = operation("execution", lambda: self.executor(response.generated_sql))
            if result["status"] == "rejected":
                response.status = "VALIDATION_REJECTED"
                response.validation_status = "rejected"
                response.validation_message = validation_reason(result.get("validation_errors", []))
                response.execution_status = "skipped"
                response.steps["execution"] = "rejected"
            elif result["status"] != "success":
                raise RuntimeError("Execution failed")
            else:
                response.columns = list(result["columns"])
                response.rows = [list(row) for row in result["rows"]]
                response.execution_status = "success"
                response.status = "SUCCESS"
        except Exception as exc:
            timed_out = isinstance(exc, TimeoutError)
            response.steps[stage] = "timeout" if timed_out else "error"
            response.status = "TIMEOUT" if timed_out else {
                "generation": "GENERATION_ERROR", "execution": "EXECUTION_ERROR",
                "validation": "VALIDATION_ERROR",
            }.get(stage, "SCHEMA_ERROR")
            if stage == "generation":
                response.generation_status = "timeout" if timed_out else "error"
                response.validation_status = "skipped"
                response.execution_status = "skipped"
            if stage == "validation":
                response.validation_status = "timeout" if timed_out else "error"
                response.execution_status = "skipped"
            if stage == "execution":
                response.execution_status = "timeout" if timed_out else "error"
            skip_after(stage)
            response.error = {
                "TIMEOUT": "The operation timed out. Please try again.",
                "GENERATION_ERROR": "SQL generation is unavailable. Please try again.",
                "EXECUTION_ERROR": "The query could not be completed.",
                "VALIDATION_ERROR": "SQL safety validation is unavailable. Execution was blocked.",
                "SCHEMA_ERROR": "Schema preparation is unavailable. Please try again.",
            }[response.status]
        finally:
            response.timings["total"] = max(0.0, perf_counter() - started)
            if on_progress:
                on_progress(dict(response.steps))
        return response


def create_service(mode="demo"):
    if mode != "demo":
        raise ValueError("Live mode requires explicit schema and Qwen adapter wiring; no demo fallback is allowed.")
    return PipelineService(DemoSchemaProvider(), DemoGenerator(), DemoExecutor())
