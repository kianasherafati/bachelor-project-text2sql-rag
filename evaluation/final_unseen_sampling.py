"""Assign source-only ERP domains and freeze deterministic candidate ordering."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata


PRIVATE = Path(__file__).resolve().parent / "final_unseen_private"
DOMAINS = [
    "sales", "purchasing", "imports/logistics", "inventory",
    "personnel/attendance", "payroll", "production", "quality",
    "assets/maintenance", "finance/treasury", "projects", "other/unclear",
]


def norm(value):
    value = unicodedata.normalize("NFKC", value or "").replace("\u200c", " ")
    return " ".join(value.split()).casefold()


def domain_for(row):
    system = norm(row.get("SystemName"))
    schema = norm(row.get("SchemaName"))
    text = norm(" ".join(str(row.get(k) or "") for k in
                         ["Title", "Description", "FormTypeName", "ReportName"]))
    # A payroll-owned physical form remains payroll even when its request text
    # uses generic words such as "balance" that also occur in inventory work.
    if schema == "gnd_hrpyr":
        return "payroll"
    if re.search(r"کنترل کیفیت|کیفی|quality|آزمایشگاه", text):
        return "quality"
    if re.search(r"پروفرما|گمرک|کوتاژ|واردات|ترخیص|بارگیری|بارنامه|لجستیک|رانند|حمل و نقل|خروج نخ|در حال ارسال", text):
        return "imports/logistics"
    if re.search(r"تولید|همبافت|بسته بندی|دوک", text):
        return "production"
    if re.search(r"برنامه نت|حکم کار|کارت فعالیت|تعمیر|نگهداری|دستگاه|سنسور|اموال", text):
        return "assets/maintenance"
    if re.search(r"حقوق|دستمزد|فیش حقوقی|تسویه حساب", text):
        return "payroll"
    if re.search(r"مرخصی|ماموریت|کارکرد|شیفت|پرسنل|کارمند|استخدام|رزومه|تردد|غیبت|حضور", text):
        return "personnel/attendance"
    if re.search(r"پروژه", text):
        return "projects"
    if re.search(r"موجودی|رسید انبار|خروج انبار|حواله خروج|کاردکس|مصرف کالا|انتقال انبار", text):
        return "inventory"
    if re.search(r"درخواست خرید|دستور خرید|استعلام خرید|صورتحساب خرید|پیش فاکتور خرید|تامین کننده", text):
        return "purchasing"
    if re.search(r"سند حسابداری|درخواست پرداخت|چک دریافتی|بانک|حساب|تفصیل|تسهیلات|ضمانت نامه|خزانه", text):
        return "finance/treasury"
    if re.search(r"فاکتور فروش|سفارش مشتری|مشتری|صورتحساب الکترونیکی|سامانه مودیان", text):
        return "sales"
    if system in {"فروش", "سامانه مودیان مالیاتی"} or schema == "gnd_crsls":
        return "sales"
    if system == "تامین کنندگان و خرید" or schema == "gnd_scpch":
        return "purchasing"
    if system in {"واردات", "لجستیک"} or schema in {"gnd_scimp", "gnd_sclog"}:
        return "imports/logistics"
    if system in {"انبار", "تعریف کالا"} or schema in {"gnd_scinv", "gnd_spgod"}:
        return "inventory"
    if system in {"حضور و غیاب", "پرسنلی و احکام", "استخدام", "ارزشیابی"} \
            or schema in {"gnd_hrcio", "gnd_hrprs", "gnd_hremp", "gnd_hrapr", "gnd_hrhrm"}:
        return "personnel/attendance"
    if system == "حقوق و دستمزد" or schema == "gnd_hrpyr":
        return "payroll"
    if system == "تولید" or schema == "gnd_scprd":
        return "production"
    if system in {"نت برنامه ای", "پایه ی نت", "نت اضطراری", "مدیریت پایش وضعیت cbm", "اموال و دارایی ها"} \
            or schema.startswith("gnd_am"):
        return "assets/maintenance"
    if system in {"خزانه داری", "حسابداری", "بانکداری الکترونیکی", "بودجه ریزی نقدی", "قراردادها"} \
            or schema.startswith("gnd_fi"):
        return "finance/treasury"
    if system == "کنترل پروژه" or schema == "gnd_pjprj":
        return "projects"
    return "other/unclear"


def allocate(counts, target=24):
    nonempty = sorted(domain for domain, count in counts.items() if count)
    if len(nonempty) > target:
        raise ValueError("Target is smaller than nonempty domain count")
    result = {domain: 1 for domain in nonempty}
    remaining = target - len(nonempty)
    total = sum(counts[d] for d in nonempty)
    quotas = {d: remaining * counts[d] / total for d in nonempty}
    for domain in nonempty:
        result[domain] += int(quotas[domain])
    left = target - sum(result.values())
    ranked = sorted(nonempty, key=lambda d: (-(quotas[d] - int(quotas[d])), d))
    for domain in ranked[:left]:
        result[domain] += 1
    return result


def main():
    target = PRIVATE / "sampling_manifest.json"
    if target.exists():
        if (PRIVATE / "selected_provenance.json").exists():
            raise ValueError("Sampling order is frozen; refusing overwrite")
        previous_sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
    else:
        previous_sha256 = None
    snapshot = json.loads((PRIVATE / "source_snapshot.json").read_text(encoding="utf-8"))
    clusters = json.loads((PRIVATE / "cluster_manifest.json").read_text(encoding="utf-8"))
    rows = {row["ID"]: row for row in snapshot["records"]}
    eligible = set(clusters["eligible_unseen_cluster_ids"])
    assignments = []
    by_domain = defaultdict(list)
    for cluster in clusters["clusters"]:
        if cluster["cluster_id"] not in eligible:
            continue
        source = rows[min(cluster["members"])]
        domain = domain_for(source)
        canonical = min(cluster["members"])
        digest = hashlib.sha256(
            f"ERP-FINAL-UNSEEN-v1 | {canonical}".encode("utf-8")
        ).hexdigest()
        item = {"cluster_id": cluster["cluster_id"], "canonical_ticket_id": canonical,
                "primary_domain": domain, "secondary_domains": [], "order_sha256": digest}
        assignments.append(item)
        by_domain[domain].append(item)
    for values in by_domain.values():
        values.sort(key=lambda item: (item["order_sha256"], item["canonical_ticket_id"]))
        for position, item in enumerate(values, 1):
            item["domain_order"] = position
    counts = Counter(item["primary_domain"] for item in assignments)
    allocation = allocate({domain: counts[domain] for domain in DOMAINS})
    payload = {
        "protocol": "ERP-FINAL-UNSEEN-v1",
        "target_case_count": 24,
        "domain_labels": DOMAINS,
        "domain_assignment_evidence": "support ticket business text and support metadata only",
        "domain_counts": {domain: counts[domain] for domain in DOMAINS},
        "domain_allocation": {domain: allocation.get(domain, 0) for domain in DOMAINS},
        "ordering": 'SHA256("ERP-FINAL-UNSEEN-v1 | " + lowest ticket ID)',
        "assignments": sorted(assignments, key=lambda item: (item["primary_domain"], item["domain_order"])),
    }
    if previous_sha256:
        payload["replaces_pre_selection_assignment_sha256"] = previous_sha256
        payload["replacement_reason"] = "Manual source-only review corrected domain precedence before target-schema investigation or selection."
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"eligible_clusters": len(assignments), "domain_counts": payload["domain_counts"],
                      "domain_allocation": payload["domain_allocation"]}, indent=2))


if __name__ == "__main__":
    main()
