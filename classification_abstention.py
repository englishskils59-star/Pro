"""Bounded linguistic repairs; no visit IDs, full-note lookup or history transfer."""
import re
from classification_semantics import client_subject

_OWN=r'الوادي(?!\s+(?:للنيل|النيل))(?!\w)'
_NUMBER=r'\d+(?:[.,]\d+)?'
_UNIT=r'(?:طن|اطنان|شيكاره|شكاير|كيس|اكياس|كيلو|كجم)'
_STOCK=re.compile(r'(?<!\w)(?:موجود\s+لديه|لديه|عنده|عند\s+العميل|مخزون\s+العميل)\s+(?:(?:بالمخزن|مخزون|كميه|علف)\s+){0,2}'+_NUMBER+r'\s*'+_UNIT+r'\s+(?:من\s+)?(?:علف\s+)?'+_OWN+r'|(?<!\w)(?:لسه\s+)?(?:باقي|متبقي)\s+عنده\s+(?:علف\s+)?'+_OWN)
_DISTRIBUTE=re.compile(r'(?<!\w)(?:[وف])?(?:توزيعه|بيوزع|يوزع)\s+(?:ل)?علف\s+'+_OWN)
_START=re.compile(r'(?<!\w)(?:متوقع\s+(?:ان\s+)?(?:يبدا|يشتغل)|من\s+المتوقع\s+ان\s+يبدا|سيبدا|هيبدا|سوف\s+يبدا)(?!\w)(?:\s+(?:العميل|التاجر|في|من|علي|خلال|بعد|بدايه|اول|اخر|الشهر|الاسبوع|الفتره|القادم|القادمه|الجاي|الجايه|المقبل|القريب|قريبا|هذا|اسبوع|شهر|\d+)){0,8}?\s+(?:ب|مع\s+)?(?:علف\s+)?(?:'+_OWN+r'|معانا(?!\w)|معنا(?!\w))')
_PAST=re.compile(r'(?<!\w)(?:[وف])?كان(?:ت)?\s+(?:شغال|شغاله|بيسحب|يتعامل|يعمل|بيوكل|بيشتري)(?!\w)(?:\s+(?:مع|في|ب|من|علف|بعلف|بمنتج|منتج)){0,4}\s+'+_OWN)
_ACCEPT_RETURN=re.compile(r'(?<!\w)(?:[وف])?(?:تم الاتفاق معه|اتفقنا معه|وافق العميل|ابدي العميل استعداده)(?:\s+\w+){0,8}?\s+(?:استخدام|العمل|التعامل|العوده|الرجوع)(?:\s+\w+){0,4}?\s+(?:ب|مع\s+)?(?:علف\s+)?'+_OWN)
_ABSENT=re.compile(r'(?<!\w)لم\s+يكن\s+(?:(?:العميل|التاجر|المربي|الموزع|صاحب\s+المزرعه)\s+)?(?:موجودا?|متواجدا?)(?!\w)|(?<!\w)(?:العميل|التاجر|المربي|صاحب\s+المزرعه)\s+لم\s+يكن\s+(?:موجودا?|متواجدا?)(?!\w)')
_NEG=re.compile(r'(?<!\w)(?:[وف])?(?:لم|لن|لا|مش|ليس|غير|ما)(?!\w)')
_PROSPECTIVE=re.compile(r'كان|سوف|سيتم|هيتم|هنوفر|سنوفر|توفير|نوفر|عرض|مخطط|متوقع|قريبا')
_OTHER_STOCK=re.compile(r'(?:يخص|ملك|خاص ب|لصالح)\s+(?:جاره|عميل اخر|الموزع|التاجر)|(?:مخزون|الكميه)\s+(?:جاره|الموزع|عميل اخر)')
_OTHER_START=re.compile(r'(?:يبدا|سيبدا|هيبدا)\s+(?:جاره|اخوه|صديقه|عميل اخر|المورد)(?!\w)')
_NUMBER_ORDER=re.compile(r'(?<!\w)(?:[وف])?تم\s+طلب\s+'+_NUMBER+r'\s*'+_UNIT+r'(?!\w)')
_MET=re.compile(r'(?<!\w)(?:قابلت\s+العميل|تمت\s+مقابله\s+العميل|تم\s+مقابله\s+العميل)(?!\w)')

def refine_abstentions(text,evidence,excluded,competitor):
    evidence=list(evidence)
    # A farm shutdown is operational context, not proof of past Wadi trade.
    if re.search(r'(?:توقف|تطهير|موقف|متوقف).*?(?:المزرعه|العنبر|العنابر)|(?:المزرعه|العنبر|العنابر).*?(?:توقف|تطهير|موقف|متوقف)',text) and not re.search(r'الوادي|معنا|معانا',text):
        evidence=[x for x in evidence if x[1]!='former']
        excluded.append('توقف المزرعة أو تطهيرها لا يثبت تعاملًا سابقًا بالوادي')
    for pattern,label in [(_STOCK,'مخزون علف الوادي موجود فعليًا لدى العميل'),(_DISTRIBUTE,'توزيع قائم لعلف الوادي منسوب للعميل')]:
        for m in pattern.finditer(text):
            prefix=' '.join(text[:m.start()].split()[-4:]);local=text[max(0,m.start()-30):m.end()+45]
            if _NEG.search(prefix) or _PROSPECTIVE.search(prefix) or not client_subject(text,m.start()) or _OTHER_STOCK.search(local):
                excluded.append('استبعاد دليل المخزون: نفي أو مستقبل أو ملكية غير منسوبة للعميل')
                continue
            evidence=[x for x in evidence if x[1]!='target']
            evidence.append((label,'current',100))
    for m in _NUMBER_ORDER.finditer(text):
        prefix=' '.join(text[:m.start()].split()[-4:])
        current=[x for x in evidence if x[1]=='current']
        independent_current=any(x[0] not in {'تم طلب','تم الطلب','طلب كمية'} for x in current)
        if not _NEG.search(prefix) and not independent_current and not any(x[1] in {'new','not_interested'} for x in evidence) and not re.search(r'تم (?:توريد|تحميل|استلام|توصيل|سحب)|استلم',text):
            tail=text[m.end():]
            rival=competitor.search(tail);own=re.search(_OWN,tail)
            rival_order=bool(rival and (not own or rival.start()<own.start()))
            third_order=bool(not client_subject(text,m.start()) or re.search(r'ل(?:جاره|اخوه|صديقه|عميل اخر)(?!\w)',tail))
            evidence=[x for x in evidence if x[1] not in {'current','target'}]
            if rival_order:evidence.append(('الطلب الرقمي يخص موردًا منافسًا لا الوادي','target',40))
            elif third_order:excluded.append('الطلب الرقمي منسوب لطرف آخر ولا يثبت استعداد العميل')
            else:evidence.append(('طلب كمية رقمية دون إثبات التوريد أو السحب لا يثبت بدء التعامل','potential',60))
    for m in _START.finditer(text):
        prefix=' '.join(text[:m.start()].split()[-4:])
        if _NEG.search(prefix) or _NEG.search(m.group()) or not client_subject(text,m.start()) or _OTHER_START.search(m.group()):
            excluded.append('استبعاد البداية المستقبلية: نفي أو جهة أخرى')
            continue
        if not any(x[1] in {'current','new'} for x in evidence):
            evidence=[x for x in evidence if x[1] not in {'target','former'}]
            evidence.append(('بداية مستقبلية صريحة مع الوادي دون تنفيذ','potential',60))
    for m in _PAST.finditer(text):
        prefix=' '.join(text[:m.start()].split()[-4:])
        if _NEG.search(prefix) or not client_subject(text,m.start()):continue
        accepted=any(not _NEG.search(' '.join(text[:a.start()].split()[-4:])) for a in _ACCEPT_RETURN.finditer(text))
        if accepted and not any(x[1] in {'current','new','not_interested'} for x in evidence):
            evidence=[x for x in evidence if x[1] not in {'former','target'}]
            evidence.append(('تعامل وادي سابق مع اتفاق عميل صريح على العودة دون دليل تنفيذ','potential',60))
        elif not any(x[1] in {'current','new','potential','not_interested'} for x in evidence):
            evidence=[x for x in evidence if x[1]!='target']
            evidence.append(('تعامل سابق بالوادي مثبت بصيغة الماضي؛ لا دليل على استمراره','former',60))
    for m in _ABSENT.finditer(text):
        prefix=' '.join(text[:m.start()].split()[-4:])
        if _NEG.search(prefix) or re.search(r'قال\s+جاره|بخصوص\s+المورد',prefix):continue
        if not _MET.search(text):evidence.append(('غياب صريح للعميل أو صاحب الزيارة','no_meeting',100))
    return evidence,excluded
