"""Retain only business-relevant private ticket text and metadata."""
import hashlib
import json
from pathlib import Path
import re
import unicodedata

PRIVATE = Path(__file__).resolve().parent / 'final_unseen_private'


def minimize(value):
    if not isinstance(value,str):
        return value
    value=unicodedata.normalize('NFKC',value)
    lines=value.replace('\r\n','\n').replace('\r','\n').splitlines()
    retained=[]
    for line in lines:
        stripped=line.strip()
        if not stripped:
            if retained and retained[-1]!='': retained.append('')
            continue
        if re.search(r'\[(?:api-inputs|username|api|position)\]\s*:',stripped,re.I):
            continue
        if re.search(r'(?:access[_ -]?token|refresh[_ -]?token|authorization|password|\bPWD\s*=|\bAcUHO\b|cookie|session[_ -]?id|api[_ -]?key)',stripped,re.I):
            continue
        if re.search(r"Error occurred in ['\"]?(?:CLIENT|SERVER)|SQL Error:\s*Check API Log Report|Error Id:\s*\d+|message:\s*(?:undefined|null)",stripped,re.I):
            continue
        if re.fullmatch(r'message\s*:?',stripped,re.I):
            continue
        if re.search(r'^(?:Traceback|at\s+[A-Za-z0-9_.<>]+\(|System\.[A-Za-z].*Exception|HTTP/[0-9]|[A-Z][A-Za-z]+Exception:)',stripped):
            continue
        if re.search(r'^(?:نام کاربر|نام و نام خانوادگی|نام درخواست کننده|موقعیت سازمانی|شماره همراه|شماره تماس|ایمیل)\s*:',stripped,re.I):
            continue
        if len(stripped)>250 and (
            stripped.startswith(('{','[','"')) or stripped.count('\\"')>3
            or bool(re.search(r'[A-Za-z0-9+/=]{40,}',stripped))
        ):
            continue
        stripped=re.sub(r'https?://\S+','[removed URL]',stripped,flags=re.I)
        stripped=re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b','[removed email]',stripped)
        stripped=re.sub(r'(?<!\d)09\d{9}(?!\d)','[removed phone]',stripped)
        stripped=re.sub(r'(?:آقای|اقای|خانم)\s+[\u0600-\u06ffA-Za-z.]+(?:\s+[\u0600-\u06ffA-Za-z.]+)?','[removed person]',stripped)
        stripped=re.sub(r'(?i)\b(?:bearer\s+)?[A-Za-z0-9+/=_-]{48,}\b','[removed encoded value]',stripped)
        # Remove machine-generated diagnostic fragments that are sometimes
        # appended to otherwise useful Persian business descriptions.
        stripped=re.sub(r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b','[removed diagnostic id]',stripped)
        stripped=re.sub(r'(?i)(?:System\.)?[A-Za-z0-9_.]+Exception\s*:?\s*','',stripped)
        stripped=re.sub(r'(?i)Exception has been thrown by the target of an invocation\.?','',stripped)
        stripped=re.sub(r'(?i)Object reference not set to an instance of an object\.?','',stripped)
        stripped=re.sub(r'(?i)Sequence contains no (?:elements|matching element)\.?','',stripped)
        stripped=re.sub(r'(?i)Invalid object name\s+[\[\]A-Za-z0-9_.]+\.?','',stripped)
        stripped=re.sub(r'(?i)Could not use view or function\s+[\[\]A-Za-z0-9_.]+[^\n]*','',stripped)
        stripped=re.sub(r'(?i)Resolution\s*:\s*[^\n]*','',stripped)
        stripped=re.sub(r'از وقفه\s*[یي]\s*ایجاد شده پوزش می\s*طلبیم!?\s*لطفا با نگهدارنده\s*[یي]\s*سیستم تماس بگیرید\.?','',stripped)
        stripped=re.sub(r'خطای پایگاه داده!?\s*لطفا با نگهدارنده\s*[یي]\s*سیستم تماس بگیرید\.?','',stripped)
        stripped=re.sub(r'خطای پایگاه داده رخ داده است\.?\s*','',stripped)
        stripped=re.sub(r'اتصال به سرور با پایان مهلت زمانی مواجه شد\.?\s*','',stripped)
        stripped=re.sub(r'(?i)The object invoked has disconnected from its clients\.?','',stripped)
        stripped=re.sub(r'(?i)The wait operation timed out\.?','',stripped)
        stripped=re.sub(r'(?i)Resolution of the dependency failed[^\u0600-\u06ff]*','',stripped)
        stripped=re.sub(r'(?i)Calling constructor[^\u0600-\u06ff]*','',stripped)
        stripped=re.sub(r'(?i)Value cannot be null\.?\s*(?:\(Parameter\s+[^)]*\))?','',stripped)
        stripped=re.sub(r"(?i)Exception of type\s*['\"]*[^'\"]*['\"]*\s+was thrown\.?",'',stripped)
        stripped=re.sub(r'(?i)Master Calculation\s*','',stripped)
        stripped=re.sub(r'(?i)\((?:Exception from HRESULT|Number)\s*[-:]?[^)]*\)','',stripped)
        stripped=re.sub(r'(?:شماره(?:\s+ی)?\s+خطا|کد\s+خطا)\s*[:：]?\s*(?:\[removed diagnostic id\]|\d+)?','',stripped)
        stripped=re.sub(r'(?i)\b(?:مدیر|کارشناس|سرپرست)\s+[\u0600-\u06ff\s]{0,24}\s+[A-Z][a-z]{2,}\b','[removed person]',stripped)
        stripped=re.sub(r'(?i)\b(?:مدیر|کارشناس|سرپرست)\s+[\u0600-\u06ff]+\s+[A-Z][A-Za-z.-]{2,}\b','[removed person]',stripped)
        stripped=re.sub(r'(?i)(?:مدیر|کارشناس|سرپرست)(?:\s+[\u0600-\u06ffA-Za-z]+){0,3}\s+[A-Z][A-Za-z.-]{2,}','[removed person]',stripped)
        stripped=re.sub(r'(?i)(?:مدیر\s+مالی|کارشناس\s+IT\s+تهران)\s+[A-Za-z.-]+','[removed person]',stripped)
        stripped=re.sub(r'[\(（]\s*(?:شناسه|ID)\s*[:：]\s*\d+\s*[\)）]','',stripped,flags=re.I)
        stripped=re.sub(r'(?i)\b(?:شناسه|ID)\s*[:：]\s*\d+\b','[removed record id]',stripped)
        stripped=re.sub(r'\.{4,}',' ',stripped)
        stripped=re.sub(r'[ \t]{2,}',' ',stripped).strip(' -:،؛')
        if stripped:
            retained.append(stripped)
    while retained and retained[-1]=='': retained.pop()
    return '\n'.join(retained)


def main():
    path=PRIVATE/'source_snapshot.json'
    before_sha256=hashlib.sha256(path.read_bytes()).hexdigest()
    source=json.loads(path.read_text(encoding='utf-8'))
    changes=[]
    for row in source['records']:
        for field in ['Title','Description','Response']:
            value=minimize(row[field])
            if value!=row[field]:
                changes.append({'ticket_id':row['ID'],'field':field,
                                'reason':'unnecessary embedded diagnostic/authentication field removal'})
                row[field]=value
    source['source_table']='gnd_grsup.tblServiceRequest'
    source['fields']=list(source['records'][0])
    source['privacy_minimization']='Removed authentication/transport fields, labeled identities, machine error templates, stack traces, URLs, serialized payloads, and encoded values; no backup retained.'
    path.write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (PRIVATE/'privacy_minimization.json').write_text(json.dumps({'changed_fields':changes,
        'input_snapshot_sha256':before_sha256,
        'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'note':'Privacy correction before clustering decisions, sampling, or target schema review.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'removed_unnecessary_diagnostic_fields':len(changes)}))


if __name__=='__main__':
    main()
