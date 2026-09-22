"""Frozen bounded reverse-FK plus explicit form-association graph retriever."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys
import time


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from graph_expanded_retriever import (  # noqa: E402
    FIXED_FK_BONUS,
    HYBRID_SEED_COUNT,
    build_outgoing_adjacency,
    graph_signal,
    rank_expanded_candidates,
)
from hybrid_retriever import HybridSchemaRetriever  # noqa: E402


GRAPH_PATH = BASE_DIR / "augmented_relationship_graph.json"
ADDITIONAL_NEIGHBOR_CAP = 10


class AugmentedGraphSchemaRetriever(HybridSchemaRetriever):
    """One-hop graph expansion with a capped metadata-derived augmentation."""

    def __init__(self):
        super().__init__()
        self.outgoing_adjacency = build_outgoing_adjacency(self.documents)
        artifact = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        if artifact["corpus_table_count"] != len(self.documents):
            raise RuntimeError("Augmented graph corpus does not match retriever corpus")
        self.graph_artifact = artifact
        self.additional_adjacency = defaultdict(dict)
        for edge in artifact["edges"]:
            families = set(edge["supporting_edge_families"])
            if families == {"outgoing_physical_fk"}:
                continue
            source = edge["source"]
            target = edge["target"]
            if target in self.outgoing_adjacency.get(source, ()):
                continue
            self.additional_adjacency[source][target] = {
                "families": sorted(families - {"outgoing_physical_fk"}),
                "provenance": [
                    item for item in edge["provenance"]
                    if item["family"] != "outgoing_physical_fk"
                ],
            }

    @staticmethod
    def _rank_key(result):
        return (
            result["final_score"], result["hybrid_score"], result["full_name"]
        )

    def rank_control(self, all_hybrid_results, top_k=50):
        seeds = all_hybrid_results[:HYBRID_SEED_COUNT]
        started = time.perf_counter()
        results, pool_size = rank_expanded_candidates(
            all_hybrid_results, seeds, self.outgoing_adjacency, top_k
        )
        elapsed = time.perf_counter() - started
        return {
            "original_hybrid_top_10": seeds,
            "expanded_candidate_pool_size": pool_size,
            "results": results,
            "expansion_and_ranking_seconds": elapsed,
        }

    def rank_augmented(self, all_hybrid_results, top_k=50):
        seeds = all_hybrid_results[:HYBRID_SEED_COUNT]
        by_name = {item["full_name"]: item for item in all_hybrid_results}
        seed_names = {item["full_name"] for item in seeds}
        started = time.perf_counter()

        candidate_names = set(seed_names)
        sources_by_candidate = defaultdict(list)
        cap_diagnostics = []
        for seed_rank, seed in enumerate(seeds, start=1):
            source = seed["full_name"]
            for target in self.outgoing_adjacency.get(source, ()):
                candidate_names.add(target)
                sources_by_candidate[target].append({
                    "table": source,
                    "rank": seed_rank,
                    "hybrid_score": seed["combined_score"],
                    "edge_families": ["outgoing_physical_fk"],
                    "edge_provenance": [],
                    "additional_edge": False,
                })

            additional = []
            for target, evidence in self.additional_adjacency.get(source, {}).items():
                additional.append({
                    "target": target,
                    "hybrid_score": by_name[target]["combined_score"],
                    **evidence,
                })
            additional.sort(
                key=lambda item: (item["hybrid_score"], item["target"]), reverse=True
            )
            admitted = additional[:ADDITIONAL_NEIGHBOR_CAP]
            excluded = additional[ADDITIONAL_NEIGHBOR_CAP:]
            for item in admitted:
                target = item["target"]
                candidate_names.add(target)
                sources_by_candidate[target].append({
                    "table": source,
                    "rank": seed_rank,
                    "hybrid_score": seed["combined_score"],
                    "edge_families": item["families"],
                    "edge_provenance": item["provenance"],
                    "additional_edge": True,
                })
            cap_diagnostics.append({
                "seed_table": source,
                "seed_rank": seed_rank,
                "additional_neighbors_considered": len(additional),
                "additional_neighbors_admitted": len(admitted),
                "cap_exclusion_count": len(excluded),
                "admitted": admitted,
                "excluded_due_to_cap": excluded,
            })

        expansion_seconds = time.perf_counter() - started
        ranking_started = time.perf_counter()
        ranked = []
        for name in candidate_names:
            hybrid_result = by_name[name]
            sources = sorted(
                sources_by_candidate.get(name, []),
                key=lambda item: (item["rank"], item["table"]),
            )
            signals = [
                graph_signal(source["rank"], source["hybrid_score"])
                for source in sources
            ]
            best_signal = max(signals, default=0.0)
            best_source = sources[signals.index(best_signal)] if signals else None
            result = dict(hybrid_result)
            result.update({
                "hybrid_score": hybrid_result["combined_score"],
                "graph_signal": best_signal,
                "fk_bonus_contribution": FIXED_FK_BONUS * best_signal,
                "final_score": hybrid_result["combined_score"] + FIXED_FK_BONUS * best_signal,
                "is_hybrid_seed": name in seed_names,
                "source_seed_tables": [item["table"] for item in sources],
                "source_edges": sources,
                "best_source_seed_rank": best_source["rank"] if best_source else None,
                "best_source_seed_hybrid_score": (
                    best_source["hybrid_score"] if best_source else None
                ),
                "best_source_edge_families": (
                    best_source["edge_families"] if best_source else []
                ),
            })
            ranked.append(result)
        ranked.sort(key=self._rank_key, reverse=True)
        ranking_seconds = time.perf_counter() - ranking_started
        return {
            "original_hybrid_top_10": seeds,
            "expanded_candidate_pool_size": len(candidate_names),
            "results": ranked[:top_k],
            "cap_diagnostics": cap_diagnostics,
            "expansion_seconds": expansion_seconds,
            "ranking_seconds": ranking_seconds,
            "expansion_and_ranking_seconds": expansion_seconds + ranking_seconds,
        }

    def retrieve_control_and_augmented(self, question, top_k=50):
        started = time.perf_counter()
        all_hybrid = self.retrieve_hybrid(question, top_k=self.index.ntotal)
        hybrid_seconds = time.perf_counter() - started
        control = self.rank_control(all_hybrid, top_k=top_k)
        augmented = self.rank_augmented(all_hybrid, top_k=top_k)
        return {
            "hybrid_seconds": hybrid_seconds,
            "all_hybrid_results": all_hybrid,
            "control": control,
            "augmented": augmented,
        }
