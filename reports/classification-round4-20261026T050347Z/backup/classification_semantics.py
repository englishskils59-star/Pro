"""Round-two business definitions. No history, supplier registry or ML inference."""
import re

def rx(s): return re.compile(s)
_ACT = rx(r'(?<!\w)(?:[وف])?(?:بيسحب|يسحب|بيشتري|يشتري|بيستخدم|يستخدم|بيوكل|شغال|يتعامل|يعمل|اشتري|اشترى|استلم|تم الطلب|تم السحب|تم سحب|تم التوريد|تم توريد|بدا التعامل|بدا العمل|بدا اول تعامل)(?!\w)')
_STOCK = rx(r'(?<!\w)(?:[وف])?(?:عنده|لديه|عند العميل|مخزون العميل)(?!\w).{0,35}?(?:مخزون|علف|بضاعه)')
_FIRST = rx(r'(?<!\w)ك?اول\s+(?:مره|تعامل|طلبيه|طلب|سحب|توريد)(?!\w)')
_DONE = rx(r'(?<!\w)(?:[وف])?(?:تم\s+(?:تنفيذ|استلام|توريد|شراء|سحب|طلب|بدء)|يتم السحب|بدا|بدانا|استلم|اشتري|اشترى|سحب)(?!\w)')
_AGREE = rx(r'(?<!\w)(?:[وف])?(?:اتفقنا|اتفق|تم الاتفاق|وافق|موافق|ابدي استعداد|مستعد|ينوي|ناوي|يريد|وعد)(?!\w)')
_START = rx(r'(?<!\w)[بل]?(?:بدء|بدايه|بدايه التعامل|بدايه العمل|اول طلبيه|اول طلب|اول تعامل|التعامل|العمل|طلب|طلبيه|الطلب|الطلبيه|الرجوع|العوده)(?!\w)')
_INCREASE = rx(r'(?<!\w)(?:زياده|يزود|نزود)(?!\w)|المسحوبات|زياده السحب')
_FUTURE = rx(r'(?<!\w)(?:سوف|سيتم|سيطلب|هيطلب|هنوفر|سنوفر|سيوفر|سنبدا|سيبدا|سيتم|سيشتري|هيشتري|ناوي|ينوي|وعد)(?!\w)|تم الاتفاق|اتفقنا|الاتفاق علي|في المستقبل')
_OFFER = rx(r'عرضنا|عرض توفير|عرض عليه|توفير مخزون|لتوفير مخزون|هنوفر|سنوفر|سوف نوفر|سيتم توفير|تجهيز مخزون')
_PAST = rx(r'(?<!\w)(?:[وف])?كان(?:ت)?(?!\w)|سابقا|في الماضي|توقف|انقطع')
_THIRD = rx(r'(?<!\w)(?:الموزع|التاجر|جاره|جار العميل|عميل اخر|عميل تاني|صديقه|اخوه|صاحبه)(?!\w)')
_CLIENT = rx(r'(?<!\w)(?:العميل|تم اقناع التاجر|تم اقناع الموزع)(?!\w)')
_VAGUE = { 'ان شاء الله','باذن الله','في الفتره القادمه','الفتره القادمه','خلال ايام','خلال اسبوع','الاسبوع القادم','الشهر القادم','بعد انتهاء الدوره','عند انتهاء الدوره','سيتم التواصل','سيتم التنسيق','سيتم متابعته','هيتم التواصل','سيتم تكرار الزياره'}


def client_subject(text,position):
    prefix=text[:position]
    other=list(_THIRD.finditer(prefix));client=list(_CLIENT.finditer(prefix))
    return not other or (client and client[-1].end()>other[-1].end())


def negated(text,start,neg):
    return bool(neg.search(' '.join(text[:start].split()[-4:])))


def analyze(clause,ours,competitor,neg):
    """Evidence belongs to a client, counterparty and temporal proposition."""
    actual=[];excluded=[]
    own_matches=list(ours.finditer(clause));rival=list(competitor.finditer(clause))
    has_ours=bool(own_matches)
    events = list(_ACT.finditer(clause))+list(_STOCK.finditer(clause)) if has_ours else []
    for event in events:
        s,e=event.span()
        following=[(m.start(),'ours') for m in own_matches if s<=m.start() and len(clause[e:m.start()].split())<=6]
        following += [(m.start(),'other') for m in rival if s<=m.start() and len(clause[e:m.start()].split())<=6]
        party=min(following)[1] if following else None
        if party!='ours':continue
        reason=None
        if re.search(r"(?:يخص|ملك|خاص ب|لصالح)\s+(?:جاره|عميل اخر|الموزع|التاجر)", clause):reason="المخزون أو التعامل يخص شخصا آخر"
        elif not client_subject(clause,s):reason='تعامل شخص آخر لا يثبت تعامل العميل'
        elif negated(clause,s,neg):reason='التعامل أو المخزون منفي'
        elif _OFFER.search(clause) or _FUTURE.search(clause[:e]):reason='عرض أو اتفاق مستقبلي دون تنفيذ'
        elif _PAST.search(" ".join(clause[:s].split()[-4:])):reason='تعامل تاريخي لا يثبت الاستمرار'
        if reason:excluded.append(reason)
        else:actual.append(event.group())
    first=False
    for first_word in _FIRST.finditer(clause):
        for event in _DONE.finditer(clause):
            lo,hi=min(event.start(),first_word.start()),max(event.end(),first_word.end())
            # The completion and first-transaction assertion must describe the
            # same local event, not an unrelated first visit or earlier task.
            if len(clause[lo:hi].split())>10:continue
            local=clause[max(0,lo-35):hi]
            valid=bool(client_subject(clause,event.start()) and not negated(clause,event.start(),neg)
                       and not _FUTURE.search(local) and not _PAST.search(local)
                       and (has_ours or not rival))
            if valid:first=True;break
        if first:break
    if first:actual.append('بدء أول تعامل فعلي')
    supplier_agreement=bool(re.search(r"(?:اتفقنا|تم الاتفاق)\s+مع\s+(?:الموزع|التاجر)",clause))
    intent=False
    agreement=_AGREE.search(clause)
    if agreement and _START.search(clause) and not supplier_agreement:
        intent=bool(client_subject(clause,agreement.start()) and not negated(clause,agreement.start(),neg)
                    and (has_ours or not rival))
    # Refusal concerning a competitor must not become refusal of Wadi.
    rejection=rx(r'رفض|رافض|يرفض|غير مهتم|لا يرغب|لا يريد').search(clause)
    competitor_refusal=bool(rejection and rival and not has_ours)
    explicit_refusal=bool(rejection and not negated(clause,rejection.start(),neg) and has_ours and not competitor_refusal)
    return {'refusal':explicit_refusal, 'supplier_agreement':supplier_agreement, 'offer':bool(_OFFER.search(clause)), 'actual':actual,'first':first,'intent':intent,'increase':bool(_INCREASE.search(clause)),
            'ours':has_ours,'competitor':bool(rival),'competitor_refusal':competitor_refusal,
            'excluded':excluded,'third': bool(_THIRD.search(clause) and not client_subject(clause,len(clause))),
            'vague':_VAGUE}
