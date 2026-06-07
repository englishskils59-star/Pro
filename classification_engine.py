# classification_engine.py
# WDI Visit Analytics Engine
# Rule-based keyword scoring classification — NO AI, NO ML, fully offline.

import pandas as pd
import numpy as np
from datetime import datetime
import re
from utils import normalize_arabic, safe_str, days_since

# ═══════════════════════════════════════════════════════════════════
# KEYWORD SCORING TABLES
# ═══════════════════════════════════════════════════════════════════

KEYWORD_RULES: list[dict] = [
    # ── CURRENT CUSTOMER  (+100) ──────────────────────────────────
    {"keyword": "تم الطلب",            "status": "current",      "score": 100},
    {"keyword": "تم السحب",            "status": "current",      "score": 100},
    {"keyword": "شغال الوادي",         "status": "current",      "score": 100},
    {"keyword": "شراء",                "status": "current",      "score": 100},
    {"keyword": "استلام",              "status": "current",      "score": 100},
    {"keyword": "طلب كمية",            "status": "current",      "score": 100},
    {"keyword": "طلب طن",              "status": "current",      "score": 100},
    {"keyword": "فاتورة",              "status": "current",      "score": 100},
    {"keyword": "عميل حالي",           "status": "current",      "score": 100},
    {"keyword": "يعمل معنا",           "status": "current",      "score": 100},
    {"keyword": "طلب جديد",            "status": "current",      "score": 100},
    {"keyword": "متابعة توريد",        "status": "current",      "score": 100},
    {"keyword": "تم التواصل تليفونيا لطلب اوردر",   "status": "current",      "score": 100},
    {"keyword": "تمت زيارته بغرض زيادة السحب",        "status": "current",      "score": 100},
    {"keyword": "اشترى",               "status": "current",      "score": 100},
    {"keyword": "طلب علف",             "status": "current",      "score": 100},
    {"keyword": "طلب شكاير",           "status": "current",      "score": 100},
    {"keyword": "تم التوريد",          "status": "current",      "score": 100},
    {"keyword": "استلم",               "status": "current",      "score": 100},
    {"keyword": "دفع",                 "status": "current",      "score": 100},
    {"keyword": "بيشتري منا",          "status": "current",      "score": 100},
    {"keyword": "عميل فعلي",           "status": "current",      "score": 100},
    {"keyword": "متابعة",              "status": "current",      "score": 100},
    {"keyword": "تم تحميل",              "status": "current",      "score": 100},
    {"keyword": "تم تنزيل",              "status": "current",      "score": 100},
    {"keyword": "تم الاتفاق على طلبية",              "status": "current",      "score": 100},
    {"keyword": "طلب نقلة",              "status": "current",      "score": 100},
    {"keyword": "طلب بضاعة",              "status": "current",      "score": 100},
    {"keyword": "زيادة استخدام علف الوادي",              "status": "current",      "score": 100},
    {"keyword": "شغال علف بريمو الوادي",              "status": "current",      "score": 100},
    {"keyword": "سيتم تحميل بضاعة",              "status": "current",      "score": 100},
    {"keyword": "التنسيق لسحب نقلة",              "status": "current",      "score": 100},
    {"keyword": "تم طلب",              "status": "current",      "score": 100},
    {"keyword": "تم مراجعه المخازن",                 "status": "current",      "score": 100},
    {"keyword": "تظبيط الشغل",                 "status": "current",      "score": 100},
    {"keyword": "تم سحب",                 "status": "current",      "score": 100},
    {"keyword": "تم توريد",                 "status": "current",      "score": 100},
    {"keyword": "تم الاتفاق على طلب",                 "status": "current",      "score": 100},
    {"keyword": "الضغط لطلب بضاعه",                 "status": "current",      "score": 100},
    {"keyword": "بيسحب الوادي",                 "status": "current",      "score": 100},
    {"keyword": "طلب وش",                 "status": "current",      "score": 100},
    {"keyword": "يتعامل مع علف الوادى",              "status": "current",      "score": 100},
    {"keyword": "سحب كميه",              "status": "current",      "score": 100},
    {"keyword": "بيوكل الوادي",              "status": "current",      "score": 100},
    {"keyword":"اوردر","status":"current","score":100},
    {"keyword":"طلبيه","status":"current","score":100},
    {"keyword":"تم الاتفاق على تنزيل","status":"current","score":100},
    {"keyword":"تحميل نقله","status":"current","score":100},
    {"keyword":"تجهيز الاوردر","status":"current","score":100},
    {"keyword":"زياده الكميه","status":"current","score":100},
    {"keyword":"تم الاتفاق على الكميه","status":"current","score":100},
    {"keyword":"سحب اوردر","status":"current","score":100},
    {"keyword":"تشغيل الوادي","status":"current","score":100},

    # ── POTENTIAL CUSTOMER  (+60) ─────────────────────────────────
    {"keyword": "مهتم",                "status": "potential",    "score": 60},
    {"keyword": "يفكر",                "status": "potential",    "score": 60},
    {"keyword": "تجربة",               "status": "potential",    "score": 60},
    {"keyword": "موعد",                "status": "potential",    "score": 60},
    {"keyword": "يرغب",                "status": "potential",    "score": 60},
    {"keyword": "طلب عرض سعر",         "status": "potential",    "score": 60},
    {"keyword": "يريد تجربة",          "status": "potential",    "score": 60},
    {"keyword": "مقابلة قادمة",        "status": "potential",    "score": 60},
    {"keyword": "زيارة ثانية",         "status": "potential",    "score": 60},
    {"keyword": "محتمل",               "status": "potential",    "score": 60},
    {"keyword": "محتاج خصم أعلى",      "status": "potential",        "score": 60},
    {"keyword": "تظبيط الخصومات",      "status": "potential",        "score": 60},
    {"keyword": "اقتنع",               "status": "potential",    "score": 60},
    {"keyword": "مقتنع",               "status": "potential",    "score": 60},
    {"keyword": "اقتنع بالمنتج",       "status": "potential",    "score": 60},
    {"keyword": "اقتنع بالعلف",        "status": "potential",    "score": 60},
    {"keyword": "عايز يجرب",           "status": "potential",    "score": 60},
    {"keyword": "هيفكر",               "status": "potential",    "score": 60},
    {"keyword": "مش رافض",             "status": "potential",    "score": 60},
    {"keyword": "شكاير",               "status": "potential",    "score": 40},
    {"keyword": "عرض سعر",             "status": "potential",    "score": 60},
    {"keyword": "اعتراض على السعر",    "status": "potential",    "score": 40},
    {"keyword": "اعتراض على الكاش",    "status": "potential",    "score": 40},
    {"keyword": "مشكلة الكاش",         "status": "potential",    "score": 40},
    {"keyword": "بيشتغل اجل",          "status": "potential",    "score": 40},
    {"keyword": "نظام الاجل",          "status": "potential",    "score": 40},
    {"keyword": "يشتغل كاش",           "status": "potential",    "score": 30},
    {"keyword": "متحمس للعمل",                "status": "potential",    "score": 60},
    {"keyword": "موافقة مبدئية",                "status": "potential",    "score": 60},
    {"keyword": "سيتم البدء",                "status": "potential",    "score": 60},
    {"keyword": "ممكن يبدأ",                "status": "potential",    "score": 60},
    {"keyword": "هيبدأ معنا",                "status": "potential",    "score": 60},
    {"keyword": "ينوى العمل معنا",                "status": "potential",    "score": 60},
    {"keyword": "يريد العمل",                "status": "potential",    "score": 60},
    {"keyword": "طلب تجربة",                "status": "potential",    "score": 60},
    {"keyword": "يجرب معنا",                "status": "potential",    "score": 60},
    {"keyword": "سيتم التواصل",                "status": "potential",    "score": 60},
    {"keyword": "سيتم تكرار الزيارة",                "status": "potential",    "score": 60},
    {"keyword": "التفكير في العرض",                "status": "potential",    "score": 60},
    {"keyword": "يريد خصم أكبر",                "status": "potential",    "score": 60},
    {"keyword": "عند انتهاء الدورة",                "status": "potential",    "score": 60},
    {"keyword": "إن شاء الله ندخل الوادى",               "status": "potential",    "score": 60},
    {"keyword": "ان شاء الله ندخل الوادى",               "status": "potential",    "score": 60},
    {"keyword": "اتفقنا",               "status": "potential",    "score": 60},
    {"keyword": "تم الاتفاق معه",               "status": "potential",    "score": 60},
    {"keyword": "الاتفاق على بداية العمل",               "status": "potential",    "score": 60},
    {"keyword": "جاهز للعمل",               "status": "potential",    "score": 60},
    {"keyword": "سيبدأ معنا",               "status": "potential",    "score": 60},
    {"keyword": "الاتفاق على بداية شغل في الوادي",               "status": "potential",    "score": 40},
    {"keyword": "متحمس للعمل",               "status": "potential",    "score": 40},
    {"keyword": "منتظر تحسن",               "status": "potential",    "score": 40},
    {"keyword": "ليس لديه مانع",               "status": "potential",    "score": 40},
    {"keyword": "لا يمانع",               "status": "potential",    "score": 40},
    {"keyword": "وعد بتوفير",               "status": "potential",    "score": 40},
    {"keyword": "منفتح على العمل",                "status": "potential",    "score": 60},
    {"keyword": "هيجربتم الاتفاق على",                "status": "potential",    "score": 60},
    {"keyword": "سيبدأ معنا",                "status": "potential",    "score": 60},
    {"keyword":"مستني انتهاء الدوره","status":"potential","score":60},
    {"keyword":"بعد انتهاء الدوره","status":"potential","score":60},
    {"keyword":"سيجرب","status":"potential","score":60},
    {"keyword":"سيتم التجربه","status":"potential","score":60},
    {"keyword":"هيبدأ بعد","status":"potential","score":60},
    {"keyword":"في حال نجاح التجربه","status":"potential","score":60},
    {"keyword":"طلب التواصل لاحقا","status":"potential","score":60},
    {"keyword":"وعد بالتجربه","status":"potential","score":60},
    {"keyword":"موافق على التجربه","status":"potential","score":60},
    {"keyword":"مهتم بالسعر","status":"potential","score":60},
    {"keyword":"منتظر انتهاء العنبر","status":"potential","score":60},
    {"keyword":"بعد بيع الدوره","status":"potential","score":60},

    # ── TARGET CUSTOMER  (+40) ────────────────────────────────────
    {"keyword": "شغال نيوهوب",         "status": "target",       "score": 40},
    {"keyword": "شغال هرمان",          "status": "target",       "score": 40},
    {"keyword": "شغال الإيمان",        "status": "target",       "score": 40},
    {"keyword": "شغال منافس",          "status": "target",       "score": 40},
    {"keyword": "شغال شركة أخرى",      "status": "target",       "score": 40},
    {"keyword": "يتعامل مع شركة أخرى", "status": "target",       "score": 40},
    {"keyword": "لديه مورد حالي",      "status": "target",       "score": 40},
    {"keyword": "تعارف",               "status": "target",        "score": 40},
    {"keyword": "بيعمل بعلف الإيمان",  "status": "target",       "score": 40},
    {"keyword": "شغال الإيمان",         "status": "target",       "score": 40},
    {"keyword": "بيعمل بعلف السلام",   "status": "target",       "score": 40},
    {"keyword": "شغال السلام",          "status": "target",       "score": 40},
    {"keyword": "بيعمل بعلف المجد",    "status": "target",       "score": 40},
    {"keyword": "شغال المجد",           "status": "target",       "score": 40},
    {"keyword": "فيدميكس",             "status": "target",       "score": 40},
    {"keyword": "بيعمل بعلف",          "status": "target",       "score": 40},
    {"keyword": "يتعامل بعلف",         "status": "target",       "score": 40},
    {"keyword": "مورد تاني",           "status": "target",       "score": 40},
    {"keyword": "شغال نيوهوب",         "status": "target",       "score": 40},
    {"keyword": "يتعامل مع علف",          "status": "target",       "score": 40},
    {"keyword": "شغال علف",          "status": "target",       "score": 40},
    {"keyword": "يستخدم علف",          "status": "target",       "score": 40},
    {"keyword": "يعمل بعلف",          "status": "target",       "score": 40},
    {"keyword": "شركة أخرى",          "status": "target",       "score": 40},
    {"keyword": "مورد حالي",          "status": "target",       "score": 40},
    {"keyword": "شغال BT",          "status": "target",       "score": 40},
    {"keyword": "شغال مكة",          "status": "target",       "score": 40},
    {"keyword": "شغال الفجر",          "status": "target",       "score": 40},
    {"keyword": "زيارة تسويقية",               "status": "target",        "score": 40},
    {"keyword": "عرض المنتج",               "status": "target",        "score": 40},
    {"keyword": "شرح المنتج",               "status": "target",        "score": 40},
    {"keyword": "التعريف بالشركة",               "status": "target",        "score": 40},
    {"keyword": "أول زيارة",               "status": "target",        "score": 40},
    {"keyword": "التعرف على",               "status": "target",        "score": 40},
    {"keyword": "ليس لديه مانع ولكن",               "status": "target",        "score": 40},
    {"keyword": "لا يمانع",                 "status": "target","score": 40},
    {"keyword": "بيوكل الايمان",             "status": "target",       "score": 40},
    {"keyword": "بيوكل الفجر",             "status": "target",       "score": 40},
    {"keyword": "بيوكل نيوهوب",             "status": "target",       "score": 40},
    {"keyword": "بيوكل بي تي",             "status": "target",       "score": 40},
    {"keyword": "بيوكل علف",             "status": "target",       "score": 40},
    {"keyword": "شغال هيرمان",             "status": "target",       "score": 40},
    {"keyword": "شغال نماء",             "status": "target",       "score": 40},
    {"keyword": "شغال هايدا",             "status": "target",       "score": 40},
    {"keyword": "شغال الصلاح",             "status": "target",       "score": 40},
    {"keyword": "شغال العبور",             "status": "target",       "score": 40},
    {"keyword": "شغال القائد",             "status": "target",       "score": 40},
    {"keyword": "شغال فيدمكس",             "status": "target",       "score": 40},
    {"keyword": "شغال وادي النيل",             "status": "target",       "score": 40},
    {"keyword": "عنبر، بريمو، تم الاتفاق معه",               "status": "target",        "score": 40},
    {"keyword": "مربى، بريمو، تم الاتفاق معه",               "status": "target",        "score": 40},
    {"keyword":"شغال هايدا","status":"target","score":40},
    {"keyword":"شغال بي تي","status":"target","score":40},
    {"keyword":"شغال مكه","status":"target","score":40},
    {"keyword":"شغال الوادي للنيل","status":"target","score":40},
 
    # ── NEW CUSTOMER  (+80) ───────────────────────────────────────
    {"keyword": "أول زيارة",           "status": "new",          "score": 80},
    {"keyword": "عميل جديد",           "status": "new",          "score": 80},
    {"keyword": "بدأ العمل",           "status": "new",          "score": 80},
    {"keyword": "بداية العمل في الوادي",           "status": "new",          "score": 80},

    # ── FORMER CUSTOMER  (+20) ────────────────────────────────────
    {"keyword": "كان يعمل معنا",       "status": "former",       "score": 20},
    {"keyword": "توقف",                "status": "former",       "score": 20},
    {"keyword": "سابق",                "status": "former",       "score": 20},
    {"keyword": "انقطع",               "status": "former",       "score": 20},
    {"keyword": "لا يطلب حاليا",       "status": "former",       "score": 20},
    {"keyword": "كان يسحب",               "status": "former",       "score": 20},
    {"keyword": "موقف شغل",               "status": "former",       "score": 20},
    {"keyword": "مبطل",               "status": "former",       "score": 20},
    {"keyword": "ارجاعه للعمل",               "status": "former",       "score": 20},
    {"keyword": "عوده للوادى",               "status": "former",       "score": 20},
    {"keyword": "كان يعمل بالوادى",               "status": "former",       "score": 20},
    {"keyword": "كان شغال مع الوادي",               "status": "former",       "score": 20},
    {"keyword": "كان بيوكل الوادي",               "status": "former",       "score": 20},
    {"keyword": "كان من عشاق الوادى",               "status": "former",       "score": 20},
    {"keyword":"كان يتعامل معنا","status":"former","score":20},
    {"keyword":"كان عميل","status":"former","score":20},
    {"keyword":"توقف عن السحب","status":"former","score":20},
    {"keyword":"انقطع عن التعامل","status":"former","score":20},
    {"keyword":"تم فقد العميل","status":"former","score":20},
    {"keyword":"كان يسحب الوادي","status":"former","score":20},
    
    # ── NOT INTERESTED  (-100) ────────────────────────────────────
    {"keyword": "رفض",                 "status": "not_interested","score": -100},
    {"keyword": "غير مهتم",            "status": "not_interested","score": -100},
    {"keyword": "مكتفي",               "status": "not_interested","score": -100},
    {"keyword": "لا يرغب",             "status": "not_interested","score": -100},
    {"keyword": "غير مقتنع",           "status": "not_interested","score": -100},
    {"keyword": "أغلق الموضوع",        "status": "not_interested","score": -100},
    {"keyword": "يتعامل مع علف دش من مدشة تابع له",    "status": "not_interested","score": -100},
    {"keyword": "يريد أجل",        "status": "not_interested","score": -100},
    {"keyword": "ليس لديه نية",                 "status": "not_interested","score": -100},
    {"keyword": "ليس لديه رغبة",                 "status": "not_interested","score": -100},
    {"keyword": "غير منفتح على إدخال منتج جديد",                 "status": "not_interested","score": -100},
    {"keyword": "المقابلة بدون جدوى",                 "status": "not_interested","score": -100},
    {"keyword": "أغلق الموضوع",                 "status": "not_interested","score": -100},
    {"keyword": "عاوز أجل",               "status": "not_interested","score": -100},
    {"keyword": "رافض",                 "status": "not_interested","score": -100},
    {"keyword": "قفل نهائيا",                 "status": "not_interested","score": -100},
    {"keyword": "لا يريد",                 "status": "not_interested","score": -100},
    {"keyword": "لا يريد التعامل كاش",                 "status": "not_interested","score": -100},
    {"keyword": "لا يريد العمل كاش",                 "status": "not_interested","score": -100},
    {"keyword": "لا يستطيع العمل كاش",                 "status": "not_interested","score": -100},
    {"keyword": "لا يستطيع ادخال",                 "status": "not_interested","score": -100},
    {"keyword": "التاجر غير منفتح",                 "status": "not_interested","score": -100},
    {"keyword":"علف خاص","status":"not_interested","score":-100},
    {"keyword":"يصنع علفه بنفسه","status":"not_interested","score":-100},
    {"keyword":"مدشه خاصه","status":"not_interested","score":-100},
    {"keyword":"يصنع الخلطه بنفسه","status":"not_interested","score":-100},
    {"keyword":"يعتمد على خلطته","status":"not_interested","score":-100},
    {"keyword":"رفض نهائيا","status":"not_interested","score":-100},
    {"keyword":"غير مقتنع بالسعر","status":"not_interested","score":-100},
    {"keyword":"لا يفكر في التغيير","status":"not_interested","score":-100},
    {"keyword":"متمسك بالمورد الحالي","status":"not_interested","score":-100},
    {"keyword":"لا توجد فرصه حاليا","status":"not_interested","score":-100},
    {"keyword":"لن يجرب","status":"not_interested","score":-100},

]

# Pre-normalize keywords once at import time for performance
for _rule in KEYWORD_RULES:
    _rule["_norm"] = normalize_arabic(_rule["keyword"])

# Status display labels
STATUS_DISPLAY = {
    "current":       "Current Customer",
    "potential":     "Potential Customer",
    "target":        "Target Customer",
    "new":           "New Customer",
    "former":        "Former Customer",
    "not_interested":"Not Interested",
    "unclassified":  "Unclassified",
}

# Priority order for tie-breaking (highest priority first)
STATUS_PRIORITY = ["current", "potential", "new", "target", "former", "not_interested", "unclassified"]


# ═══════════════════════════════════════════════════════════════════
# SINGLE-NOTE CLASSIFIER
# ═══════════════════════════════════════════════════════════════════

def classify_note(note: str, is_first_appearance: bool = False) -> dict:
    """
    Classify a single visit note using keyword scoring.

    Returns:
        {
            "suggested_status": str,   # internal key
            "display_status":   str,   # human-readable label
            "confidence":       float, # 0–100
            "score":            int,   # raw total score
            "matched_keywords": list[str],
            "reason":           str,
        }
    """
    norm_note = normalize_arabic(safe_str(note))

    # Accumulate scores per status
    score_map: dict[str, int] = {}
    matched: list[str] = []

    for rule in KEYWORD_RULES:
        if rule["_norm"] in norm_note:
            status = rule["status"]
            score_map[status] = score_map.get(status, 0) + rule["score"]
            matched.append(rule["keyword"])

    # First-appearance bonus for "new"
    if is_first_appearance:
        score_map["new"] = score_map.get("new", 0) + 80
        if "أول زيارة" not in matched:
            matched.append("(first appearance in database)")

    # Determine winner
    if not score_map:
        suggested = "unclassified"
        total_score = 0
    else:
        # Sort by score descending, then by priority for ties
        sorted_statuses = sorted(
            score_map.keys(),
            key=lambda s: (-score_map[s], STATUS_PRIORITY.index(s) if s in STATUS_PRIORITY else 99),
        )
        suggested = sorted_statuses[0]
        total_score = score_map[suggested]

    # Confidence: map score to 0-100 range
    # Max single-keyword score is 100; cap confidence at 99%
    if total_score <= 0:
        confidence = 0.0
    else:
        confidence = min(99.0, round((total_score / max(total_score, 100)) * 100, 1))
        # Boost confidence slightly for very high scores
        if total_score >= 200:
            confidence = min(99.0, confidence + 10)

    # Build reason string
    if matched:
        kw_list = "، ".join(matched)
        reason = f"تطابق الكلمات المفتاحية: {kw_list}"
    elif is_first_appearance:
        reason = "أول ظهور للعميل في قاعدة البيانات"
    else:
        reason = "لا توجد كلمات مفتاحية — غير مصنف"

    return {
        "suggested_status": suggested,
        "display_status":   STATUS_DISPLAY.get(suggested, suggested),
        "confidence":       confidence,
        "score":            total_score,
        "matched_keywords": matched,
        "reason":           reason,
    }


# ═══════════════════════════════════════════════════════════════════
# BATCH CLASSIFIER  (full DataFrame)
# ═══════════════════════════════════════════════════════════════════

def classify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify every row in the DataFrame.

    Adds columns:
        Suggested Status, Display Status, Confidence Score,
        Raw Score, Matched Keywords, Classification Reason

    Also tracks customer journey (first appearance rule).
    Optimized for 50,000+ rows.
    """
    df = df.copy()
    df = df.sort_values("Visit Date", ascending=True).reset_index(drop=True)

    # Track which customer names have been seen (for first-appearance rule)
    seen_customers: set[str] = set()

    suggested_statuses = []
    display_statuses   = []
    confidences        = []
    raw_scores         = []
    matched_keywords   = []
    reasons            = []

    notes_col    = df["Visit Notes"].tolist()    if "Visit Notes"    in df.columns else [""] * len(df)
    customer_col = df["Customer Name"].tolist()  if "Customer Name"  in df.columns else [""] * len(df)

    for i in range(len(df)):
        note     = safe_str(notes_col[i])
        customer = safe_str(customer_col[i]).strip()

        is_first = customer not in seen_customers
        if customer:
            seen_customers.add(customer)
            new_keywords = ["أول زيارة", "تعارف", "عميل جديد"]
            has_new_keyword = any(kw in safe_str(note) for kw in new_keywords)
        result = classify_note(note, is_first_appearance=is_first and has_new_keyword)

        suggested_statuses.append(result["suggested_status"])
        display_statuses.append(result["display_status"])
        confidences.append(result["confidence"])
        raw_scores.append(result["score"])
        matched_keywords.append(", ".join(result["matched_keywords"]))
        reasons.append(result["reason"])

    df["Suggested Status"]      = suggested_statuses
    df["Display Status"]        = display_statuses
    df["Confidence Score"]      = confidences
    df["Raw Score"]             = raw_scores
    df["Matched Keywords"]      = matched_keywords
    df["Classification Reason"] = reasons

    return df


# ═══════════════════════════════════════════════════════════════════
# CUSTOMER JOURNEY TRACKER
# ═══════════════════════════════════════════════════════════════════

def build_customer_journey(classified_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each unique customer, build a journey summary:
        Customer Name, First Visit Date, Last Visit Date,
        Visit Count, Days Since Last Visit,
        Status History (list), Latest Status, Latest Confidence
    """
    if classified_df.empty:
        return pd.DataFrame()

    today = pd.Timestamp(datetime.today().date())
    records = []

    grp = classified_df.sort_values("Visit Date").groupby("Customer Name", sort=False)

    for customer_name, group in grp:
        visits        = group.sort_values("Visit Date")
        first_visit   = visits["Visit Date"].min()
        last_visit    = visits["Visit Date"].max()
        visit_count   = len(visits)
        days_since_lv = days_since(last_visit, today)

        # Journey: list of (date, status) tuples
        history = []
        for _, row in visits.iterrows():
            history.append({
                "visit_date": row["Visit Date"],
                "status":     row.get("Display Status", "Unclassified"),
                "notes":      safe_str(row.get("Visit Notes", "")),
                "sales_rep":  safe_str(row.get("Sales Rep Name", "")),
            })

        latest_row        = visits.iloc[-1]
        latest_status     = safe_str(latest_row.get("Display Status", "Unclassified"))
        latest_confidence = latest_row.get("Confidence Score", 0.0)

        # Build readable status history string
        status_history_str = " → ".join(
            [f"[{h['visit_date'].strftime('%Y-%m-%d') if pd.notnull(h['visit_date']) else '?'}] {h['status']}"
             for h in history]
        )

        records.append({
            "Customer Name":       customer_name,
            "First Visit Date":    first_visit,
            "Last Visit Date":     last_visit,
            "Visit Count":         visit_count,
            "Days Since Last Visit": days_since_lv,
            "Latest Status":       latest_status,
            "Latest Confidence":   latest_confidence,
            "Status History":      status_history_str,
            "_journey":            history,   # kept for detail views; dropped on export
            "Governorate":         safe_str(group["Governorate"].iloc[-1]) if "Governorate" in group.columns else "",
            "District":            safe_str(group["District"].iloc[-1])    if "District"    in group.columns else "",
            "Sales Rep Name":      safe_str(group["Sales Rep Name"].iloc[-1]) if "Sales Rep Name" in group.columns else "",
        })

    journey_df = pd.DataFrame(records)
    return journey_df


# ═══════════════════════════════════════════════════════════════════
# NOT-VISITED SEGMENTS
# ═══════════════════════════════════════════════════════════════════

def customers_not_visited(journey_df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Return customers whose last visit was more than `days` days ago."""
    if journey_df.empty or "Days Since Last Visit" not in journey_df.columns:
        return pd.DataFrame()
    mask = journey_df["Days Since Last Visit"].fillna(9999) >= days
    return journey_df[mask].copy()


# ═══════════════════════════════════════════════════════════════════
# CONFIGURABLE KEYWORD EDITOR SUPPORT
# ═══════════════════════════════════════════════════════════════════

def get_rules_dataframe() -> pd.DataFrame:
    """Return current keyword rules as a DataFrame for display/editing."""
    rows = [
        {
            "Keyword":   r["keyword"],
            "Status":    STATUS_DISPLAY.get(r["status"], r["status"]),
            "Score":     r["score"],
        }
        for r in KEYWORD_RULES
    ]
    return pd.DataFrame(rows)


def apply_custom_rules(df: pd.DataFrame, custom_rules: list[dict]) -> pd.DataFrame:
    """
    Re-classify using a custom rules list.
    custom_rules: [{"keyword": str, "status": str (internal key), "score": int}, ...]
    """
    # Temporarily replace KEYWORD_RULES
    global KEYWORD_RULES
    original = KEYWORD_RULES[:]
    KEYWORD_RULES = custom_rules
    for rule in KEYWORD_RULES:
        rule["_norm"] = normalize_arabic(rule["keyword"])
    result = classify_dataframe(df)
    KEYWORD_RULES = original
    return result
