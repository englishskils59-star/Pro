"""Owner-approved operational policy; no ML and no business-data writes."""
import re
import pandas as pd
from utils import normalize_arabic

DEFAULT_REASON = "مستهدف افتراضيًا لعدم توفر دليل تعامل أو اهتمام أو رفض، وعدم وجود حالة تاريخية موثوقة"
FOLLOWUP_REASON = "متابعة عميل قائم وفق تعريف الأعمال المعتمد من صاحب البرنامج"
FOLLOWUP = re.compile(r"(?<!\w)(?:[وف])?(?:متابعه|متابعت|متابعه العميل|متابعته|متابعتهم)(?!\w)")


def refine_policy(text, evidence, excluded):
    """Explicit contents precede visit-title/follow-up evidence."""
    statuses = {s for _, s, _ in evidence}
    absent=re.search(r"(?<!\w)(?:[وف])?(?:لم يكن(?:\s+(?:العميل|التاجر|المربي))?\s+(?:موجودا?|متواجدا?)|لم يتواجد(?:\s+(?:العميل|التاجر|المربي))?|غير موجود|غير متواجد)(?!\w)",text)
    if absent and not re.search(r"المندوب|مخزون|العلف|بضاعه|المنافس",text):
        evidence.append(("لم تتم مقابلة العميل في هذه الزيارة",'no_meeting',100))
    # Refusal of an offer/terms is final only when explicitly rejected, not negotiated.
    refusal = re.search(r"(?<!\w)(?:[وف])?(?:رفض|رافض|يرفض)\s+(?:نهائيا\s+)?(?:التعامل|الشروط|شروطنا|العرض|الكاش|الدفع نقدا)(?!\w)", text)
    if refusal and not re.search(r"(?:لم|لا|مش|غير)\s+(?:يكن\s+)?$", text[:refusal.start()]) and not re.search(r"(?:التعامل مع|عرض|شروط)\s+(?:المنافس|نيوهوب|هايدا)", text):
        evidence.append(("رفض صريح للتعامل أو للشروط المعروضة", "not_interested", 100))
        statuses.add("not_interested")
    # Follow-up to persuade a first start/return expresses pre-execution intent.
    intent = re.search(r"(?:لاقناعه|لاقناع العميل|للتفاوض|التفاوض|يتفاوض|يفكر|التفكير|تفاوض|موافق|وافق|وعد|مستعد|استعداد).{0,45}(?:بدء التعامل|بدايه التعامل|تجربه الوادي|تجربه علف الوادي|الرجوع|العوده|للعمل معنا|لطلب|بالطلب)", text)
    if intent and not re.search(r"(?:[وف])?(?:لم|لن|لا|ليس|غير|مش)\s+(?:يكن\s+)?[يو]?$", text[:intent.start()]) and not re.search(r"(?:وافق|موافق|يفكر|تفاوض)\s+(?:الموزع|جاره|صديقه|شخص اخر)",intent.group()):
        if not statuses.intersection({'current','new','not_interested'}):
            evidence = [e for e in evidence if e[1] not in {'former','target'}]
            evidence.append(("تفاوض أو استعداد لبدء التعامل أو العودة قبل التنفيذ", "potential", 60))
    statuses = {s for _, s, _ in evidence}
    if 'not_interested' in statuses and re.search(r'رفض|رافض|يرفض|غير مهتم|لا يريد|لا يرغب|غير مناسب',text):
        excluded.extend("مضمون آخر مع رفض صريح: " + label for label,s,_ in evidence if s != 'not_interested')
        evidence = [e for e in evidence if e[1]=='not_interested']
    elif 'potential' in statuses and 'former' in statuses and not re.search(r'لم يوافق|لم يرد|لن يعود|وافق الموزع|وافق جاره',text) and re.search(r"يريد الرجوع|يريد العوده|وافق.*العوده|موافق.*الرجوع|تفاوض.*العوده|تم الاتفاق.*(?:العوده|الرجوع)",text):
        evidence = [e for e in evidence if e[1] not in {'former','target'}]
        excluded.append("القبول أو التفاوض على العودة لاحق للتعامل السابق ولا يثبت التنفيذ")
    statuses = {s for _, s, _ in evidence}
    if FOLLOWUP.search(text) and not statuses:
        blocked = re.search(r"(?:لم|لن|لا|غير|ليس|مش|سيتم|سوف|قررنا|سنقوم)\s+(?:تتم\s+)?(?:المتابعه|متابعه)|متابعه\s+(?:جاره|جار العميل|صديقه|عميل اخر)|متابعه.*(?:المنافس|نيوهوب|هايدا)|(?:الرفض|توقف|متوقف|سابق|لاقناعه|للبدء|بدء التعامل|لم يبدا)|(?:لا|لم|لن|مش|ليس)\s+(?:يتعامل|يشتري|يسحب|يستخدم|بيشتري|بيسحب)|سيتم المتابعه|المتابعه لاحقا|لم يكن مهتم|لم يوافق|لن يوافق|لم يقبل|لن يقبل", text)
        if not blocked:
            evidence.append((FOLLOWUP_REASON, 'current', 70))
            excluded=[x for x in excluded if not x.startswith(('متابعة:', 'متابعه المخزن:', 'متابعت العميل'))]
    return evidence, excluded


def decision_basis(reason, source=''):
    if source == 'Manual': return 'Manual'
    if DEFAULT_REASON in str(reason): return 'DefaultTarget'
    if 'حالة تاريخية موثوقة' in str(reason): return 'History'
    if FOLLOWUP_REASON in str(reason): return 'Followup'
    if 'تعامل من موزع مثبت بالسجلات' in str(reason): return 'SupplierReference'
    return 'TextEvidence'


def default_result(result):
    out = dict(result)
    if out['suggested_status'] == 'unclassified':
        out.update(suggested_status='target', display_status='Target Customer', confidence=0.0,
                   score=0, matched_keywords=[], reason=DEFAULT_REASON + ' | تشخيص الملاحظة: ' + out['reason'])
    return out


def trusted_references(refs):
    if refs is None: return None
    refs = refs.copy()
    reasons = refs.get('Classification Reason', pd.Series('',index=refs.index)).fillna('').astype(str)
    basis = refs.get('Classification Basis', pd.Series('',index=refs.index)).fillna('')
    manual = refs.get('Override Source', pd.Series('',index=refs.index)).eq('Manual')
    fallback = basis.isin(['History','DefaultTarget','SupplierReference']) | reasons.str.contains('مستهدف افتراضي|حالة تاريخية موثوقة|تعامل من موزع مثبت بالسجلات',regex=True)
    return refs[~fallback | manual]


def apply_history_and_default(frame, reference_records):
    from classification_engine import classify_note, STATUS_DISPLAY
    from classification_context import text_value
    out=frame.copy()
    def identity(row):
        # Exact full stored identity plus geography. Never use a name alone.
        for col in ('Customer ID','Customer Code'):
            v=text_value(row.get(col))
            if v:return (col,v)
        name=text_value(row.get('Customer Name Original')) or text_value(row.get('Customer Name'))
        gov=text_value(row.get('Governorate')); district=text_value(row.get('District'))
        if len(name.split())<2 or not (gov or district):return None
        return ('identity',name,gov,district)
    refs=trusted_references(reference_records)
    pools=[out]
    if refs is not None and not refs.empty:pools.append(refs)
    history={}
    for pool in pools:
        for _,row in pool.iterrows():
            key=identity(row); when=pd.to_datetime(row.get('Visit Date'),errors='coerce',utc=True)
            if key is None or pd.isna(when):continue
            reason=text_value(row.get('Classification Reason'))
            if decision_basis(reason,text_value(row.get('Override Source'))) in {'History','DefaultTarget','SupplierReference'}:continue
            if row.get('Override Source')=='Manual' and row.get('Display Status')=='No Meeting':continue
            if row.get('Override Source')=='Manual' and row.get('Display Status') not in ('Unclassified','No Meeting'):
                status=row.get('Display Status'); source='اعتماد يدوي محفوظ'; evidence=reason
            else:
                # Re-evaluate legacy saved evidence, never promote an old fallback.
                direct=classify_note(row.get('Visit Notes'))
                if decision_basis(direct['reason'])=='DefaultTarget':continue
                status=direct['display_status'];source='دليل ملاحظة سابقة';evidence=direct['reason']
            if status not in set(STATUS_DISPLAY.values())-{'Unclassified','No Meeting'}:continue
            history.setdefault(key,[]).append((when,status,source,evidence))
    for i,row in out.iterrows():
        if row['Display Status']!='Unclassified':continue
        key=identity(row); when=pd.to_datetime(row.get('Visit Date'),errors='coerce',utc=True)
        earlier=[x for x in history.get(key,[]) if not pd.isna(when) and x[0]<when]
        chosen=None
        if earlier:
            last=max(x[0] for x in earlier); at_last=[x for x in earlier if x[0]==last]
            manual=[x for x in at_last if x[2]=='اعتماد يدوي محفوظ']
            at_last=manual or at_last
            if len({x[1] for x in at_last})==1:chosen=at_last[0]
        if chosen:
            date,status,source,evidence=chosen
            status='Current Customer' if status=='New Customer' else status
            reverse={v:k for k,v in STATUS_DISPLAY.items()}
            out.at[i,'Display Status']=status;out.at[i,'Suggested Status']=reverse[status]
            out.at[i,'Classification Reason']=f'حالة تاريخية موثوقة لنفس هوية العميل: {status}؛ المصدر: {source} بتاريخ {date.isoformat()}؛ ليست دليلا جديدا من نص هذه الزيارة. سبب المرجع: {evidence}'
            out.at[i,'Confidence Score']=0.0;out.at[i,'Raw Score']=0;out.at[i,'Matched Keywords']=''
        else:
            out.at[i,'Display Status']='Target Customer';out.at[i,'Suggested Status']='target'
            out.at[i,'Classification Reason']=DEFAULT_REASON+' | تشخيص الملاحظة: '+str(row['Classification Reason'])
            out.at[i,'Confidence Score']=0.0;out.at[i,'Raw Score']=0;out.at[i,'Matched Keywords']=''
    out['Classification Basis']=[decision_basis(r,s) for r,s in zip(out['Classification Reason'],out.get('Override Source',pd.Series('',index=out.index)))]
    return out
