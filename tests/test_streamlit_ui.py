import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class StreamlitUITests(unittest.TestCase):
    def app(self):
        script = Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py"
        app = AppTest.from_file(script, default_timeout=20)
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_clear_resets_complete_state(self):
        app = self.app()
        self.assertTrue(next(button for button in app.button if button.label == "Clear").disabled)
        app.selectbox[0].select("Regional sales").run()
        self.assertEqual(app.text_area[0].value, "Show synthetic sales totals by region.")
        self.assertFalse(next(button for button in app.button if button.label == "Clear").disabled)
        next(button for button in app.button if button.label == "Generate & Run").click().run()
        self.assertEqual(app.session_state["response"].status, "SUCCESS")
        next(button for button in app.button if button.label == "Clear").click().run()
        self.assertEqual(app.text_area[0].value, "")
        self.assertEqual(app.selectbox[0].value, "Choose an example…")
        self.assertIsNone(app.session_state["response"])

    def test_all_demo_scenarios_render_without_exception(self):
        app = self.app()
        expected = {
            "Regional sales": "SUCCESS",
            "Empty result": "SUCCESS",
            "Insufficient schema": "INSUFFICIENT_SCHEMA",
            "Validation rejected": "VALIDATION_REJECTED",
            "Generation error": "GENERATION_ERROR",
            "Execution error": "EXECUTION_ERROR",
            "Timeout": "TIMEOUT",
        }
        for scenario, status in expected.items():
            app.selectbox[0].select(scenario).run()
            next(button for button in app.button if button.label == "Generate & Run").click().run()
            self.assertFalse(app.exception, scenario)
            self.assertEqual(app.session_state["response"].status, status)


if __name__ == "__main__":
    unittest.main()
