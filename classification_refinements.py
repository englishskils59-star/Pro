"""General text patterns derived from explicit human development reviews.

No IDs, individual note lookup, distributor-name mapping, or ML training.
"""
import re
from classification_semantics import client_subject

OWN=r'(?:علف\s+)?الوادي(?!\s+(?:للنيل|النيل))'
# Feed analytics: chicks and cooling equipment do not prove Wadi feed use.
_NONFEED=re.compile(r'((?:كتكوت|كتاكيت|تبريد)(?:\s+\w+){0,3}\s+)الوادي')
_FACT=re.compile(r'(?<!\w)(?:[وف])?(?:شغال|يعمل|تعمل|بيعمل|بتعمل|بيشتغل|بيسحب|بيشتري|يستخدم|بيستخدم|بيوكل|يتعامل)(?!\w)(?:\s+(?:بالفعل|حاليا|بعلف|بمنتج|علف|منتج|ب|في|من)){0,4}\s+الوادي(?!\s+(?:للنيل|النيل))|عميل حالي للوادي|عميل الوادي شغال')
_ADOPT=re.compile(r'(?:الاعتماد(?: الكلي)? علي|توزيع)\s+علف الوادي(?:\s+\w+){0,4}\s+(?:التوزيع|مخزنه|مخزنه|لديه|توزيعه|مع توزيعه)')
_INCREMENT=re.compile(r'(?:زياده|يزود|زود|بيزود|تزويد|زياده في)\s+(?:كمي(?:ه|اته|ته)|المسحوبات|مسحوباته|السحب)|زياده مسحوباته')
_EXISTING=re.compile(r'الكميه (?:الموجوده|المتبقيه)|كم(?:يه|يات) (?:موجوده|متبقيه)|مخزون (?:قائم|متبق)|اخر سحب')
_RENEW=re.compile(r'كميه جديده|نقله جديده|طلب\s*\d|طلب اضافي|سحب اضافي|ترتيب.*طلب|الترتيب.*طلب|تم طلب كميه|هيتم طلب')
_START_DONE=re.compile(r'تم البدء (?:في )?(?:العمل|التعامل).*الوادي.*(?:البدء في السحب|تم السحب|استلم|تم تحميل)')
_NEG=re.compile(r'(?<!\w)(?:[وف])?(?:لم|لن|لا|مش|ليس|غير)(?!\w)')
_HYPOTHETICAL=re.compile(r'في حاله رفض|اذا رفض|لو رفض|في حال رفض|لو.*رفض')
_ROUTE_REFUSAL=re.compile(r'رفض(?:\w*)\s+(?:العمل|التعامل|تشغيله).*من خلال|رافض العمل من خلال موزع|الذي رفض|الذى رفض')
_REJECTION=re.compile(r'غير مهتم|رفض التعامل مع الوادي|لا يرغب|لا يريد التعامل|مش هيدخل|مش هيقدر يدخل|معندوش نيه|لا ينوي|غير متفتح|غير منفتح|غير مناسب له العمل كاش|تراجع عن طلب|لا يريد المخاطره|رافض نهائيا')
_NEGOTIATE=re.compile(r'تم (?:الحديث|لحديث|التحدث|التفاوض|تنسيق)|تكلمنا|اتكلمنا|تحدثنا|دارت مفاوضات|المفاوضات|التفاوض|عرضت عليه|تم عرض|بعرض العلف|الحديث عن|اتفقت|اتفقنا|تم الاتفاق|الاتفاق علي|تحديد.*ميعاد|حددت.*ميعاد|طلب معرفه|عرض.*الاسعار|نتكلم في الاسعار|عاوز اجل|نعمل جلسه تاني|توصيله باقرب|حددت معاه ميعاد|واتفق|الموافقه عليه')
_BUSINESS=re.compile(r'الوادي|العلف|البريمو|المنتج|منتج|العمل|الشغل|طلب|طلبيه|نقله|الاسعار|الخصم|خصم|التسديد|تمويل|العموله|التجربه|يجرب|زياره')
_READY=re.compile(r'مستعد|استعداد|نيته للعمل|ابدي.*نيته|مرحب|متحمس|مقتنع|اقتنع|اقناعه|اقناعه|اقناع.*تمويل|ابدي مرونه|امكانيه (?:تشغيل|تجربه|اشتراك|استخدام)|ممكن يشتغل|ممكن.*يجرب|من الممكن.*يعمل|من الممكن.*يتم اقناعه|سيفكر|هيفكر|الالتزام بسحب|لا يمانع|غير ممانع|نرجع نشتغل|لايجاد طريقه للعمل|منتظر.*موزع.*لتجربه|محتاج العمل مباشر|هيعرض المنتج|وعدوا بالمناقشه|هيشتغل|هيدخل معانا|عايز يشتغل')
_FUTURE_ORDER=re.compile(r'سيتم طلب|هيتم طلب|سيقوم بطلب|هيطلب|هيسحب|ستطلب|هايشتغل|هيشتغل|هيجرب|هينزل العلف|سبطلب|سوف يطلب|طلبيه خلال|وعد.*(?:طلب|سحب|البدايه|العمل)|تم الوعد|تواصل.*لامكانيه طلب|سيتم التواصل.*طلب|الترتيب علي.*سحب|اول ما ابدا اتصل')
_ORDER_ONLY=re.compile(r'تم طلب (?:نقله|كميه)|تم تسجيل طلب')
_RECEIVED=re.compile(r'تم (?:التحميل|تحميل|التوصيل|توصيل|السحب|سحب|الاستلام|استلام|التوريد|توريد)|استلم|لسه منزل|تم تنزيل|تم تنفيذ')
_PAST_OWN=re.compile(r'كان\s+(?:شغال|يسحب|يتعامل|يعمل|بيوكل).*(?:الوادي|معنا)|عميل (?:سابق|ساابق)\s+(?:للوادي|لنا)|اشتغل.*(?:في|مع) الوادي.*بعد كده')
# A postposed past predicate describes stopped trade, not a new current fact.
_STOPPED_TRADE=re.compile(r'(?:شغال|يتعامل)\s+(?:\w+\s+){0,2}الوادي\s+كان\s+(?:شغال|يتعامل)\s+وتوقف(?!\w)')
_RETURN_AGREED=re.compile(r'(?<!\w)(?:[وف])?(?:وافق|موافق|اتفقنا معه|تم الاتفاق معه|ابدي استعداده|ابدي رغبته).*(?:العوده|الرجوع|نرجع|نشتغل|العمل|التعامل)|(?:التفاوض).*(?:العموله|التسديد|التساهل|اعاده نزول)|غير ممانع|سيقوم بطلب|سيتم نزول المنتج|(?:بس|بشرط)\s+(?:ظبط|تظبط|تعديل)\s+(?:لي\s+)?(?:الخصم|السعر|نظام السداد)')
_WE_RETURN=re.compile(r'(?<!\w)نرجع\s+نشتغل(?!\w)')
_PAST_BARRIER=re.compile(r'صعبه في الفتره|صعب حاليا|رفض فكره الكاش|حاليا مبطل')
_SELF_MIX=re.compile(r'علف دش من مدشه|مدشه تابع له|مدشه داخل المزرعه')

def mask_nonfeed(text):
    changed=_NONFEED.sub(r'\1جهة_غير_علف',text)
    return changed, changed!=text


def refine(text,evidence,excluded):
    """Return explanatory evidence under explicit counterparty/time conditions."""
    evidence=list(evidence)
    actual=False
    actual_positions=[]
    for match in _FACT.finditer(text):
        prefix=' '.join(text[:match.start()].split()[-4:])
        if not _NEG.search(prefix) and not re.search(r'كان|سوف|سيتم|هيتم|امكانيه|امكانيه|بدء',prefix) and client_subject(text,match.start()):
            actual=True
            actual_positions.append(match.start())
    if _ADOPT.search(text) and not re.search(r'سيتم الاعتماد|هيتم الاعتماد|سوف.*الاعتماد',text):actual=True
    stopped_match=_STOPPED_TRADE.search(text)
    stopped_trade=bool(stopped_match)
    if stopped_trade:
        actual=any(pos>stopped_match.end() for pos in actual_positions)
        excluded.append('التعامل المذكور موصوف لاحقًا بأنه توقف؛ لا يثبت الاستمرار')
    increased=bool(_INCREMENT.search(text) and re.search(r'عميل|مسحوب|سحب|كميه|شغال|يتعامل',text))
    ongoing=bool((_EXISTING.search(text) and _RENEW.search(text)) or re.search(r'اخر سحب.*الاستمرار',text))
    # Owner-authorized context: increase over existing quantities, not distributor identity.
    context_current=(increased or ongoing) and not (re.search(r'ك?اول مره|اول طلبيه',text) and _FUTURE_ORDER.search(text))
    if context_current:
        actual=True
        evidence.append(('زيادة كميات أو متابعة مخزون قائم وطلب إضافي وفق تعريف صاحب البرنامج','current',100))
    first=bool(_START_DONE.search(text))
    if first and not re.search(r'لم يتم البدء|سيتم البدء|هيتم البدء',text):
        evidence.append(('بدء العمل بالوادي وبدء السحب معًا وفق اعتماد صاحب البرنامج','new',100))
        actual=True
    elif actual:evidence.append(('تعامل قائم بعلف الوادي مثبت في النص','current',100))
    potential=bool((_NEGOTIATE.search(text) and _BUSINESS.search(text)) or _READY.search(text) or _FUTURE_ORDER.search(text))
    if re.fullmatch(r'تم عرض (?:العلف|المنتج)',text.strip()):
        potential=False
        evidence=[x for x in evidence if x[1]!='potential']
        evidence.append(('عرض منتج فقط دون تفاوض أو استعداد مثبت','target',40))
    # First-person plural wishes do not establish the customer's acceptance.
    accepted_return=any(
        not _NEG.search(' '.join(text[:m.start()].split()[-4:]))
        and (not re.match(r'(?:[وف])?(?:وافق|موافق)(?!\w)',m.group()) or client_subject(text,m.start()))
        and not re.match(r'(?:[وف])?(?:وافق|موافق)\s+(?:الموزع|المندوب|المورد)(?!\w)',m.group())
        for m in _RETURN_AGREED.finditer(text)
    )
    weak_return=bool(_WE_RETURN.search(text) and not accepted_return)
    if weak_return:
        potential=bool((_NEGOTIATE.search(text) and _BUSINESS.search(text)) or _FUTURE_ORDER.search(text))
        evidence=[x for x in evidence if not (x[1]=='potential' and _WE_RETURN.search(x[0]))]
        excluded.append('رغبة بصيغة نرجع نشتغل لا تثبت موافقة العميل على العودة')
    hypothetical=bool(_HYPOTHETICAL.search(text));route=bool(_ROUTE_REFUSAL.search(text))
    explicit_refusal=bool(_REJECTION.search(text)) and not hypothetical
    tentative=bool(re.search(r'سيفكر|امكانيه.*يجرب|ممكن.*يجرب|وافق.*موزع اخر|ابدي مرونه',text))
    if tentative and potential and not re.search(r'رافض نهائيا|رفض نهائيا|غير مهتم',text):explicit_refusal=False
    if hypothetical or (route and potential):
        evidence=[x for x in evidence if x[1]!='not_interested'];excluded.append('الرفض افتراضي أو يخص مسار التوريد لا موقف العميل من المنتج')
    # Asking for credit is negotiation, distinct from explicitly rejecting cash.
    if potential and not explicit_refusal:
        evidence=[x for x in evidence if not (x[1]=='not_interested' and re.search(r'اجل|مستقر مع|ملتزم بكميات',x[0]))]
    former=bool(stopped_trade or (_PAST_OWN.search(text) and re.search(r'توقف|مبطل|سابق|ساابق|بعد كده',text)))
    actionable_return=accepted_return
    if weak_return and not former and not re.search(OWN,text):
        evidence=[x for x in evidence if x[1]!='former']
        excluded.append('توقف تعامل غير منسوب للوادي لا يثبت أنه عميل وادي سابق')
    if former and not actual:
        evidence=[x for x in evidence if x[1] not in {'current','new'}]
        evidence.append(('تعامل وادي سابق متوقف أو استبدل بجهة أخرى','former',60))
        if actionable_return and not _PAST_BARRIER.search(text):
            evidence=[x for x in evidence if x[1]=='no_meeting' or x[1] not in {'former','target'}]
            evidence.append(('نية رجوع مع تفاوض أو ترتيب صريح دون بدء تعامل جديد','potential',60))
            potential=True
        else:
            potential=False
            if _PAST_BARRIER.search(text) or not re.search(r'يريد الرجوع|مهتم|يرغب',text):
                evidence=[x for x in evidence if x[1] not in {'potential','target','not_interested'}]
    if _SELF_MIX.search(text) and not potential and not actual:
        evidence=[x for x in evidence if x[1] not in {'not_interested','former'}]
        evidence.append(('خلط ذاتي لعلف آخر دون رفض صريح للوادي','target',40))
    order_only=bool(_ORDER_ONLY.search(text) and not _RECEIVED.search(text))
    planned=bool(_FUTURE_ORDER.search(text))
    if (potential or order_only or planned) and not actual and not former and not explicit_refusal:
        evidence=[x for x in evidence if x[1] not in {'current','new','target','not_interested'}]
        evidence.append(('تفاوض أو استعداد أو ترتيب طلب قبل إثبات التنفيذ','potential',60))
    if actual and not explicit_refusal:
        removable={'potential','target'}
        if stopped_trade and any(pos>stopped_match.end() for pos in actual_positions):removable.add('former')
        evidence=[x for x in evidence if x[1] not in removable]
        excluded.append('التفاوض أو ترتيب الطلب الإضافي لا يلغي التعامل القائم')
    if explicit_refusal and not actual:
        has_positive_interest=any(x[0] in {'مهتم','يرغب','متحمس للعمل'} for x in evidence if x[1]=='potential')
        evidence=[x for x in evidence if x[1]!='target' and (has_positive_interest or x[1]!='potential')]
        evidence.append(('رفض حالي صريح أو عدم استعداد لإدخال منتج جديد','not_interested',100))
    if first:evidence=[x for x in evidence if x[1]!='current']
    return evidence,excluded
