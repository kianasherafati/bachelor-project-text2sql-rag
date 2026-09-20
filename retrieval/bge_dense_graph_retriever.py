"""Dense-only BGE-M3 seed ranking followed by frozen outgoing-FK expansion."""

from __future__ import annotations

import math
import time

from bge_m3_retriever import BGEM3SchemaRetriever
from graph_expanded_retriever import (
    FIXED_FK_BONUS,
    HYBRID_SEED_COUNT,
)


class BGEDenseGraphRetriever(BGEM3SchemaRetriever):
    """Apply the frozen graph policy directly to BGE dense results."""

    def retrieve_bge_dense_graph(self, question: str, top_k: int = 10):
        if top_k <= 0:
            return {
                "original_bge_dense_top_10": [],
                "expanded_candidate_pool_size": 0,
                "results": [],
                "all_dense_results": [],
                "all_expanded_candidates": [],
                "timing": {
                    "dense_ranking_seconds": 0.0,
                    "graph_expansion_ranking_seconds": 0.0,
                    "total_seconds": 0.0,
                },
            }

        total_started = time.perf_counter()
        dense_started = time.perf_counter()
        all_dense = self._all_dense_results(question)
        dense_seconds = time.perf_counter() - dense_started
        seeds = all_dense[:HYBRID_SEED_COUNT]
        if len({result["full_name"] for result in seeds}) != HYBRID_SEED_COUNT:
            raise ValueError("BGE dense seeds are not ten distinct tables")

        graph_started = time.perf_counter()
        by_name = {result["full_name"]: result for result in all_dense}
        seed_names = {result["full_name"] for result in seeds}
        candidates = set(seed_names)
        sources_by_candidate = {}
        for seed_rank, seed in enumerate(seeds, start=1):
            source_name = seed["full_name"]
            for target in self.outgoing_adjacency.get(source_name, ()):
                candidates.add(target)
                sources_by_candidate.setdefault(target, []).append({
                    "table": source_name,
                    "rank": seed_rank,
                    "raw_bge_cosine": seed["raw_bge_cosine"],
                    "dense_score": seed["dense_score"],
                })

        ranked = []
        for name in candidates:
            dense = by_name[name]
            sources = sorted(
                sources_by_candidate.get(name, []),
                key=lambda item: (item["rank"], item["table"]),
            )
            source_signals = [
                source["dense_score"] / math.log2(source["rank"] + 1)
                for source in sources
            ]
            best_signal = max(source_signals, default=0.0)
            contribution = FIXED_FK_BONUS * best_signal
            item = dict(dense)
            item.update({
                "bge_dense_rank": dense["global_dense_rank"],
                "is_bge_dense_seed": name in seed_names,
                "source_seed_tables": [source["table"] for source in sources],
                "source_seeds": sources,
                "graph_signal": best_signal,
                "fk_bonus_contribution": contribution,
                "final_score": dense["dense_score"] + contribution,
            })
            ranked.append(item)
        ranked.sort(
            key=lambda result: (
                result["final_score"],
                result["dense_score"],
                result["full_name"],
            ),
            reverse=True,
        )
        for rank, result in enumerate(ranked, start=1):
            result["final_rank"] = rank
        graph_seconds = time.perf_counter() - graph_started
        return {
            "original_bge_dense_top_10": seeds,
            "expanded_candidate_pool_size": len(candidates),
            "results": ranked[: min(top_k, len(ranked))],
            "all_dense_results": all_dense,
            "all_expanded_candidates": ranked,
            "timing": {
                "dense_ranking_seconds": dense_seconds,
                "graph_expansion_ranking_seconds": graph_seconds,
                "total_seconds": time.perf_counter() - total_started,
            },
        }
