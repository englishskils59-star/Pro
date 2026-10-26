"""Private, offline context matcher. Shared text/name helpers remain unchanged."""
from functools import lru_cache
import re
import unicodedata
import pandas as pd
from utils import normalize_arabic
from classification_semantics import analyze
from classification_refinements import refine, mask_nonfeed
from classification_abstention import refine_abstentions

ENGINE_VERSION = "context-rules-5-operational-followup"
DEFINITIONS_VERSION = "owner-approved-2026-10-26-operational-followup"
SCORE_NOTE = "درجة قوة أدلة قواعد وليست احتمال صحة إحصائي"


def text_value(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (ValueError, TypeError):
        pass
    return str(value).strip()


def normalize_note(value):
    text = normalize_arabic(unicodedata.normalize("NFKC", text_value(value))).casefold()
    # Classification-only token repair; original records and visit-key normalization stay untouched.
    text = re.sub(r"(?<=\d)(?=[\u0621-\u064a])|(?<=[\u0621-\u064a])(?=\d)", " ", text)
    text = re.sub(r"(?<!\w)(يوم|ايام|شهر|اسبوع)(?=(?:يتعامل|بيسحب|يعمل|بيستخدم|يشتغل)(?!\w))", r"\1 ", text)
    text = re.sub(r"(?<!\w)(طن|اطنان|شيكاره|كجم)(?=الوادي(?!\w))", r"\1 ", text)
    return " ".join(text.split())


# These base expressions describe a visit/task/object, not completed trade.
_WEAK_CURRENT = {normalize_note(s) for s in [
    "متابعة", "متابعه المخزن", "متابعت العميل و المخزن", "تم التواصل مع العميل",
    "تم مراجعه المخازن", "تظبيط الشغل", "الضغط لطلب بضاعه", "تم الضغط على التاجر",
    "موجود لديه", "متبقي عنده", "خلص عنده", "بالمخزن", "لديه بالمخزن",
    "اوردر", "طلبيه", "تجهيز الاوردر", "تجهيز حموله", "زياده الكميه", "باع الدورة",
    "خلص الدوره", "طلبات التكويد", "هيبعت طلبات التكويد", "تفريده", "ترتيب التفريده",
    "جارى الاتفاق مع جامبو", "التنسيق لزيادة الكميات", "التنسيق لزيادة المسحوبات",
]}
_GENERIC_BUY = {normalize_note(s) for s in ["شراء", "اشترى", "استلام", "استلم", "دفع", "فاتورة"]}
_SPLIT = re.compile(r"[،,؛;.!؟?\n]+|(?<!\w)(?:و?لكن(?:ه)?|بينما|ثم)(?!\w)|\s+(?=و(?:تم|اشترى|استلم|دفع|مهتم|يريد|كان|رفض|غير|لم|العميل|هو|يرفض|اتفقنا|لا|لن|بيسحب|بيستخدم|يتعامل|عنده|لديه)(?!\w))")
_NEG = re.compile(r"(?<!\w)(?:[وف])?(?:لم|لن|لا|مش|ليس|غير|ما)(?!\w)")
_FUTURE = re.compile(r"(?<!\w)(?:سوف|سيتم|سيطلب|هيطلب|هينزل|هيطهر|سنطلب|سيشتري|سيستلم|هيشتري|ناوي|ينوي|وعد|نتمني|اذا|لو)(?!\w)|تم الاتفاق|التنسيق ل|الاتفاق علي|بعد انتهاء|عند انتهاء|القادم|القادمه")
_OURS = re.compile(r"(?<!\w)(?:منا|معنا|الوادي)(?!\w)(?!\s+(?:النيل|للنيل))")
_COMPETITOR = re.compile(r"(?<!\w)(?:[وف]?[بل]?)?(?:المنافس|منافس|شركه اخري|مورد اخر|مورد تاني|نيوهوب|هايدا|الايمان|فيدميكس|فيدمكس|الشروق|وادي النيل|الوادي للنيل)(?!\w)")
# Extra phrases express the same existing statuses, never a new status.
CONTEXT_RULES = [
    {"keyword": "لم يكن متواجدا", "status": "no_meeting", "score": 100},
    {"keyword": "شراء من الوادي", "status": "current", "score": 100},
    {"keyword": "شراء من المنافس", "status": "target", "score": 40},
    {"keyword": "يريد الرجوع", "status": "potential", "score": 60},
    {"keyword": "يريد العودة", "status": "potential", "score": 60},
]


@lru_cache(maxsize=16)
def compile_rules(signature):
    by_phrase = {}
    for phrase, label, status, score in signature:
        by_phrase.setdefault(phrase, []).append((label, status, score))
    alternatives = sorted(by_phrase, key=lambda s: (-len(s), s))
    # Lookahead visits every start; longest phrase wins at a given start.
    expression = r"(?<!\w)(?:[وف])?(?=(" + "|".join(re.escape(s) for s in alternatives) + r")(?!\w))"
    return re.compile(expression), by_phrase


def decide(normalized, signature):
    normalized, masked_nonfeed = mask_nonfeed(normalized)
    matcher, by_phrase = compile_rules(signature)
    evidence, excluded = [], []
    signals = []
    for clause in _SPLIT.split(normalized):
        if not clause.strip():
            continue
        signal = analyze(clause, _OURS, _COMPETITOR, _NEG)
        signals.append(signal)
        excluded.extend(signal["excluded"])
        if signal["refusal"]:
            evidence.append(("رفض صريح للتعامل مع الوادي", "not_interested", 100))
        if signal["first"]:
            evidence.append(("بدء أول تعامل فعلي", "new", 100))
        elif signal["actual"]:
            evidence.append(("تعامل فعلي للعميل بعلف الوادي: " + "، ".join(signal["actual"]), "current", 100))
        if signal["intent"]:
            evidence.append(("استعداد أو اتفاق على بدء التعامل دون إثبات التنفيذ", "potential", 60))
        hits = []
        for m in matcher.finditer(clause):
            start, end = m.span(1)
            hits.append((start, end, m.group(1)))
        # A longer phrase consumes its whole interval, also across statuses.
        kept = []
        for start, end, phrase in sorted(hits, key=lambda h: (-(h[1]-h[0]), h[0])):
            if any(start < b and a < end for a,b,_ in kept):
                continue
            kept.append((start, end, phrase))
        for start, end, phrase in sorted(kept):
            prefix = clause[:start]
            # Bound negation to the nearest proposition and last four words.
            prefix = re.split(r"(?<!\w)(?:و|ف)?(?:تم|اشترى|استلم|دفع)(?!\w)", prefix)[-1] if not phrase.startswith('تم ') else prefix
            local = " ".join(prefix.split()[-4:])
            negated = bool(_NEG.search(local))
            for label, status, score in by_phrase[phrase]:
                why = None
                if status in {"current", "new"} and signal["offer"]:
                    why = "عرض توفير لا يثبت مخزون العميل أو بدء التعامل"
                elif status == "potential" and signal["supplier_agreement"]:
                    why = "اتفاق مع مورد لا يثبت استعداد العميل"
                elif status == "new" and not signal["first"]:
                    why = "لا يوجد دليل على أن التعامل الفعلي هو الأول"
                elif status in {"current", "new"} and signal["third"]:
                    why = "التعامل منسوب لشخص آخر"
                elif status == "potential" and phrase in signal["vague"] and not signal["intent"]:
                    why = "صياغة عامة دون استعداد أو اتفاق واضح"
                elif status == "not_interested" and signal["competitor_refusal"]:
                    why = "الرفض يخص المنافس لا الوادي"
                elif negated:
                    why = "نفي محلي للدليل"
                elif status == "current" and phrase in _WEAK_CURRENT:
                    why = "متابعة أو إجراء دون دليل تعامل مكتمل"
                elif status in {"current", "new"} and _FUTURE.search(local + " " + phrase):
                    why = "نية أو اتفاق مستقبلي لا يثبت التنفيذ"
                elif status == "current" and re.search(r"(?<!\w)(?:[وف])?كان(?:ت)?(?!\w)", local):
                    why = "تعامل ماض لا يثبت استمرار التعامل"
                elif status in {"current", "new"} and _COMPETITOR.search(clause) and not _OURS.search(clause):
                    status, score = "target", 40
                elif status == "current" and phrase in _GENERIC_BUY and not _OURS.search(clause):
                    why = "جهة التعامل أو إتمامه غير واضح"
                if why:
                    excluded.append(f"{label}: {why}")
                else:
                    evidence.append((label, status, score))
    # Resolve only relationships explicitly supported by counterparty/time.
    actual_ours = any(s["actual"] for s in signals)
    first_actual = any(s["first"] for s in signals)
    competitor_context = any(s["competitor"] for s in signals) or any(s == "target" for _,s,_ in evidence)
    has_refusal = any(s == "not_interested" for _,s,_ in evidence)
    remove = set()
    if has_refusal and competitor_context and not actual_ours:
        remove.add("target")
        excluded.append("التعامل مع منافس لا يناقض الرفض الصريح للوادي")
    if actual_ours:
        remove.add("target")
        excluded.append("دليل التعامل الفعلي بالوادي أقوى من مجرد وجود مورد منافس")
        if any(s["increase"] for s in signals):
            remove.add("potential")
            excluded.append("الاتفاق على زيادة التعامل الحالي ليس بداية تعامل محتملة")
    if first_actual:
        remove.add("current")
        excluded.append("التعامل مثبت والأولية مثبتة؛ الحالة New وليست مجرد Current")
    evidence = [item for item in evidence if item[1] not in remove]
    evidence, excluded = refine(normalized, evidence, excluded)
    evidence, excluded = refine_abstentions(normalized, evidence, excluded, _COMPETITOR)
    from classification_policy import refine_policy
    evidence, excluded = refine_policy(normalized, evidence, excluded)
    if masked_nonfeed:excluded.append("ذكر كتكوت أو تبريد الوادي لا يثبت التعامل بعلف الوادي")
    # One strongest item per status: repetition/synonyms cannot inflate scores.
    scores = {}
    for _, status, score in evidence:
        scores[status] = max(scores.get(status, 0), score)
    real = set(scores) - {"no_meeting"}
    if real:
        scores.pop("no_meeting", None)
    conflict = (len(real) > 1 and not real <= {"target", "potential"})
    ordered = sorted(scores, key=lambda s: (-scores[s], s))
    suggested = "unclassified" if conflict or not ordered else ordered[0]
    score = scores.get(suggested, 0)
    confidence = min(99.0, float(score)) if score else 0.0
    if len(ordered) > 1 and score:
        confidence = round(confidence * score / sum(scores.values()), 1)
    decisive = list(dict.fromkeys(label for label,status,_ in evidence if status == suggested))
    if conflict:
        reason = "أدلة متعارضة تحتاج مراجعة: " + "، ".join(dict.fromkeys(f"{s}: {label}" for label,s,_ in evidence))
    elif decisive:
        reason = "أدلة القرار: " + "، ".join(decisive)
    else:
        reason = "أدلة غير كافية — غير مصنف"
    if not evidence and _FUTURE.search(normalized):
        excluded.append("صياغة مستقبلية وحدها لا تثبت تنفيذ التعامل")
    if excluded:
        reason += " | استبعاد: " + "؛ ".join(dict.fromkeys(excluded))
    if not conflict:
        others = [label for label,status,_ in evidence if status != suggested]
        if others:
            reason += " | أدلة أخرى لا تغيّر القرار: " + "، ".join(dict.fromkeys(others))
    return suggested, confidence, int(score), tuple(decisive), reason + " | " + SCORE_NOTE


@lru_cache(maxsize=20000)
def cached_decide(normalized, signature):
    return decide(normalized, signature)


def manual_result(display, status_display):
    reverse = {v:k for k,v in status_display.items()}
    return {"suggested_status": reverse[display], "display_status": display,
            "confidence": 100.0, "score": 0, "matched_keywords": [],
            "reason": "تصنيف يدوي معتمد محفوظ؛ 100 علامة اعتماد يدوي وليست احتمال صحة إحصائي"}


def apply_manual_result(frame, index, display, status_display):
    result = manual_result(display, status_display)
    for column,key in [('Suggested Status','suggested_status'),('Display Status','display_status'),
                       ('Confidence Score','confidence'),('Raw Score','score'),('Classification Reason','reason')]:
        frame.at[index,column] = result[key]
    frame.at[index,'Matched Keywords'] = ''
    frame.at[index,'Override Source'] = 'Manual'
    frame.at[index,'Classification Basis'] = 'Manual'
