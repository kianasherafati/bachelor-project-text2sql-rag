"""Prepare source-only duplicate review; never reads ERP retrieval artifacts."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import unicodedata

PRIVATE = Path(__file__).resolve().parent / 'final_unseen_private'


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value or '').split())


def tokens(value):
    return set(re.findall(r'\w+', normalize(value).casefold()))


def business_text(row):
    """Return sanitized requirement wording, suppressing machine-only tickets."""
    title=normalize(row.get('Title'))
    description=normalize(row.get('Description'))
    description=re.sub(r'(?i)\bmessage:\s*(?:Object must implement IConvertible\.?|String .*? valid (?:TimeSpan|DateTime)\.?|undefined|null)\s*',' ',description)
    description=normalize(description)
    generic_title=bool(re.fullmatch(r'(?:فرم|گزارش)\s+[^:：]+[:：]?',title,re.I))
    if generic_title and not description:
        return ''
    return normalize(title+' '+description)


def main():
    source = PRIVATE / 'source_snapshot.json'
    snapshot = json.loads(source.read_text(encoding='utf-8'))
    rows = snapshot['records']
    ids = {row['ID'] for row in rows}
    if len(ids) != len(rows):
        raise ValueError('Source IDs are not unique')
    text = {r['ID']: business_text(r) for r in rows}
    sets = {i: tokens(t) for i,t in text.items()}
    flags = []
    for a,b in itertools.combinations(rows,2):
        x,y = a['ID'],b['ID']
        if not text[x] or not text[y]:
            continue
        union = sets[x] | sets[y]
        score = len(sets[x] & sets[y])/len(union) if union else 0
        reasons = []
        if text[x] and text[x] == text[y]:
            reasons.append('exact_normalized_duplicate')
        elif score >= .85:
            reasons.append('jaccard_at_least_0.85')
        same_reference = any(a[k] is not None and a[k] == b[k] for k in ['IDofFormType','IDofReport'])
        same_label = any(normalize(a[k]) and normalize(a[k]) == normalize(b[k]) for k in ['FormTypeName','ReportName'])
        if (same_reference or same_label) and score >= .50:
            reasons.append('same_form_or_report_and_jaccard_at_least_0.50')
        if reasons:
            flags.append({'left':x,'right':y,'jaccard':score,'reasons':reasons})
    # Numeric matches only flag references for review; they never create edges.
    for row in rows:
        combined = '\n'.join(str(row.get(k) or '') for k in ['Title','Description','Response'])
        found = set()
        for match in re.finditer(r'(?:درخواست|تیکت|پیرو|ادامه|ticket|request)[^\n\d]{0,45}([0-9۰-۹٠-٩]{4,7})',combined,re.I):
            number = int(match.group(1))
            if number in ids and number != row['ID']:
                found.add(number)
        for other in sorted(found):
            flags.append({'left':min(row['ID'],other),'right':max(row['ID'],other),
                          'jaccard':None,'reasons':['possible_explicit_ticket_reference']})
    payload = {
        'algorithm_version':2,
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'normalization':'NFKC and collapsed whitespace',
        'near_duplicate_threshold':.85,
        'same_reference_wording_review_threshold':.50,
        'threshold_frozen_before_review_or_sampling':True,
        'manual_review_rubric':'Would the same reporting question and answer satisfy both requests?',
        'business_text_policy':'Sanitized Title + Description only; machine-only generic form/report titles and known framework message fragments suppressed.',
        'flags':flags,
        'metadata_structure_note':'Source table has no explicit parent-ticket column. Text references are reviewed, never automatically treated as ticket links.',
    }
    target = PRIVATE / 'duplicate_review_queue.json'
    if target.exists():
        if not (PRIVATE/'privacy_minimization.json').exists() or (PRIVATE/'cluster_manifest.json').exists():
            raise ValueError('Review queue is frozen; refusing overwrite')
        previous=json.loads(target.read_text(encoding='utf-8'))
        if previous['source_sha256']==payload['source_sha256'] and previous.get('algorithm_version')==payload['algorithm_version']:
            raise ValueError('Review queue already matches source; refusing overwrite')
        payload['replaces_pre_minimization_queue_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        payload['replacement_reason']='Source privacy minimization before any clustering decisions or sampling; identical thresholds.'
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest = {'snapshot_sha256':payload['source_sha256'],'source_table':'gnd_grsup.tblServiceRequest',
                'source_database':snapshot['source_database'],'captured_at_utc':snapshot['captured_at_utc'],
                'customer_scope':snapshot['customer_id'],'row_count':len(rows),
                'fields':list(rows[0]),'status':'private_source_frozen; clustering pending'}
    (PRIVATE/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    from collections import Counter
    print(json.dumps({'tickets':len(rows),'review_pairs':len(flags),
                      'flag_types':dict(Counter(r for f in flags for r in f['reasons'])),
                      'source_sha256':payload['source_sha256']},indent=2))


if __name__ == '__main__':
    main()
