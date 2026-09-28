"""Apply private human duplicate decisions and freeze requirement clusters."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path


PRIVATE = Path(__file__).resolve().parent / "final_unseen_private"


class UnionFind:
    def __init__(self, values):
        self.parent = {value: value for value in values}

    def find(self, value):
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            value, self.parent[value] = self.parent[value], root
        return root

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def main():
    snapshot_path = PRIVATE / "source_snapshot.json"
    queue_path = PRIVATE / "duplicate_review_queue.json"
    decisions_path = PRIVATE / "duplicate_decisions.json"
    registry_path = PRIVATE / "exclusion_registry.json"
    target = PRIVATE / "cluster_manifest.json"
    if target.exists():
        raise ValueError("Cluster manifest is frozen; refusing overwrite")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ids = {row["ID"] for row in snapshot["records"]}
    pair_keys = {f"{min(item['left'], item['right'])}:{max(item['left'], item['right'])}"
                 for item in queue["flags"]}
    decision_keys = {item["pair"] for item in decisions["decisions"]}
    if pair_keys != decision_keys:
        raise ValueError("Every flagged pair must have exactly one human decision")

    uf = UnionFind(ids)
    for item in decisions["decisions"]:
        if item["merge"]:
            left, right = map(int, item["pair"].split(":"))
            uf.union(left, right)

    members = defaultdict(list)
    for ticket_id in sorted(ids):
        members[uf.find(ticket_id)].append(ticket_id)
    clusters = []
    for values in sorted(members.values(), key=lambda x: x[0]):
        stable_key = ",".join(map(str, values))
        clusters.append({
            "cluster_id": "rc-" + hashlib.sha256(stable_key.encode()).hexdigest()[:16],
            "members": values,
            "member_count": len(values),
        })

    historical = {item["ticket_id"] for item in registry["tickets"]
                  if item.get("directly_inspected")}
    contaminated = [c for c in clusters if historical.intersection(c["members"])]
    contaminated_ids = {ticket for c in contaminated for ticket in c["members"]}
    eligible = [c for c in clusters if not historical.intersection(c["members"])]
    payload = {
        "algorithm_version": 1,
        "source_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "review_queue_sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(),
        "decisions_sha256": hashlib.sha256(decisions_path.read_bytes()).hexdigest(),
        "manual_review_rubric": decisions["manual_review_rubric"],
        "ticket_count": len(ids),
        "requirement_cluster_count": len(clusters),
        "clusters": clusters,
        "historical_ticket_count": len(historical),
        "contaminated_cluster_ids": [c["cluster_id"] for c in contaminated],
        "contaminated_cluster_count": len(contaminated),
        "tickets_removed_by_cluster_contamination": len(contaminated_ids),
        "eligible_unseen_cluster_count": len(eligible),
        "eligible_unseen_cluster_ids": [c["cluster_id"] for c in eligible],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in [
        "ticket_count", "requirement_cluster_count", "historical_ticket_count",
        "contaminated_cluster_count", "tickets_removed_by_cluster_contamination",
        "eligible_unseen_cluster_count"]}, indent=2))


if __name__ == "__main__":
    main()
