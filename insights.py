# insights.py
# WDI Visit Analytics Engine
# Advanced analytics: promises, next-best-visit, competitors,
# productivity, data quality, engine accuracy, period comparison, coverage map.

import re
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils import normalize_arabic, safe_str, STATUS_COLORS, NON_STATUS_LABELS

from dashboard import PLOTLY_TEMPLATE  # registers the "wdi_dark" template

PRIMARY   = "#2DD4BF"
SECONDARY = "#4C9AFF"
ACCENT    = "#70AD47"
BG        = "rgba(0,0,0,0)"


# ═══════════════════════════════════════════════════════════════════
# 1) PROMISE TRACKER — وعود مؤجلة مستخرجة من الملاحظات
# ═══════════════════════════════════════════════════════════════════

# expected_days = تقدير المدة المتوقعة لتنفيذ الوعد قبل اعتباره مستحقاً
PROMISE_RULES = [
    {"keyword": "خلال ايام",             "label": "وعد بالبدء خلال أيام",        "expected_days": 7},
    {"keyword": "خلال اسبوع",            "label": "وعد بالبدء خلال أسبوع",       "expected_days": 10},
    {"keyword": "الاسبوع القادم",        "label": "وعد بالبدء الأسبوع القادم",   "expected_days": 10},
    {"keyword": "الشهر القادم",          "label": "وعد بالبدء الشهر القادم",     "expected_days": 35},
    {"keyword": "بعد انتهاء الدوره",     "label": "بعد انتهاء الدورة",           "expected_days": 45},
    {"keyword": "عند انتهاء الدوره",     "label": "بعد انتهاء الدورة",           "expected_days": 45},
    {"keyword": "مستني انتهاء الدوره",   "label": "بعد انتهاء الدورة",           "expected_days": 45},
    {"keyword": "بعد بيع الدوره",        "label": "بعد بيع الدورة",              "expected_days": 45},
    {"keyword": "بعد خروج الدوره",       "label": "بعد انتهاء الدورة",           "expected_days": 45},
    {"keyword": "منتظر نزول الكتكوت",    "label": "منتظر نزول الكتكوت",          "expected_days": 30},
    {"keyword": "منتظر سعر الكتكوت",     "label": "منتظر سعر الكتكوت",           "expected_days": 30},
    {"keyword": "مع نزول سعر الكتكوت",   "label": "منتظر سعر الكتكوت",           "expected_days": 30},
    {"keyword": "بعد استقرار السوق",     "label": "منتظر استقرار السوق",         "expected_days": 30},
    {"keyword": "مع تحرك السوق",         "label": "منتظر استقرار السوق",         "expected_days": 30},
    {"keyword": "مع استقرار الاسعار",    "label": "منتظر استقرار الأسعار",       "expected_days": 30},
    {"keyword": "بعد ثبات الاسعار",      "label": "منتظر استقرار الأسعار",       "expected_days": 30},
    {"keyword": "سيجرب",                 "label": "وعد بالتجربة",                "expected_days": 21},
    {"keyword": "وعد بالتجربه",          "label": "وعد بالتجربة",                "expected_days": 21},
    {"keyword": "موافق على التجربه",     "label": "وعد بالتجربة",                "expected_days": 21},
    {"keyword": "سيتم التجربه",          "label": "وعد بالتجربة",                "expected_days": 21},
    {"keyword": "هيجرب في عنبر",         "label": "وعد بالتجربة",                "expected_days": 21},
    {"keyword": "طلب التواصل لاحقا",     "label": "طلب التواصل لاحقاً",          "expected_days": 14},
    {"keyword": "سيتم التواصل",          "label": "متابعة موعودة",               "expected_days": 14},
    {"keyword": "سيتم تكرار الزياره",    "label": "زيارة ثانية موعودة",          "expected_days": 14},
    {"keyword": "زياره ثانيه",           "label": "زيارة ثانية موعودة",          "expected_days": 14},
    {"keyword": "سيتم متابعته",          "label": "متابعة موعودة",               "expected_days": 14},
    {"keyword": "هيتم التواصل",          "label": "متابعة موعودة",               "expected_days": 14},
    {"keyword": "تم ترتيب ميعاد",        "label": "ميعاد متفق عليه",             "expected_days": 7},
    {"keyword": "ترتيب ميعاد",           "label": "ميعاد متفق عليه",             "expected_days": 7},
    {"keyword": "مقابله قادمه",          "label": "ميعاد متفق عليه",             "expected_days": 7},
    {"keyword": "هيفكر",                 "label": "سيفكر في العرض",              "expected_days": 14},
    {"keyword": "التفكير في العرض",      "label": "سيفكر في العرض",              "expected_days": 14},
    {"keyword": "هيبدا بعد",             "label": "وعد بالبدء لاحقاً",           "expected_days": 30},
    {"keyword": "سيتم البدء",            "label": "وعد بالبدء",                  "expected_days": 21},
    {"keyword": "هيبدا معنا",            "label": "وعد بالبدء",                  "expected_days": 21},
    {"keyword": "سيبدا معنا",            "label": "وعد بالبدء",                  "expected_days": 21},
    {"keyword": "مستعد للبدء",           "label": "وعد بالبدء",                  "expected_days": 21},
    {"keyword": "وعد بالبدء",            "label": "وعد بالبدء",                  "expected_days": 21},
    {"keyword": "وعد بالتعامل",          "label": "وعد بالتعامل",                "expected_days": 21},
    {"keyword": "وعد بتوفير",            "label": "وعد بالتوفير",                "expected_days": 21},
]
for _r in PROMISE_RULES:
    _r["_norm"] = normalize_arabic(_r["keyword"])


def extract_promises(classified_df: pd.DataFrame,
                     journey_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract deferred promises from visit notes and evaluate each one:
      ✅ تحول لعميل حالي  — the customer converted after the promise
      🔁 تمت متابعته      — a later visit happened after the promise
      🔥 مستحق الآن       — due date passed with no follow-up visit
      ⏳ لم يستحق بعد     — due date still in the future
    Only each customer's LATEST promise is kept.
    """
    if classified_df.empty or "Visit Notes" not in classified_df.columns:
        return pd.DataFrame()

    today = pd.Timestamp(datetime.today().date())
    df = classified_df.copy()
    df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")

    # last visit date per customer (any visit counts as a follow-up)
    last_visit = df.groupby("Customer Name")["Visit Date"].max()

    # customers currently "Current" and since when (first conversion date fallback: last current visit)
    cur_since = (df[df["Display Status"] == "Current Customer"]
                 .groupby("Customer Name")["Visit Date"].min())

    latest_status = {}
    if not journey_df.empty and "Latest Status" in journey_df.columns:
        latest_status = dict(zip(journey_df["Customer Name"], journey_df["Latest Status"]))

    records = []
    notes = df["Visit Notes"].astype(str).tolist()
    for i, note in enumerate(notes):
        norm = normalize_arabic(note)
        if not norm:
            continue
        for rule in PROMISE_RULES:
            if rule["_norm"] in norm:
                row = df.iloc[i]
                records.append({
                    "Customer Name":  safe_str(row.get("Customer Name")),
                    "Governorate":    safe_str(row.get("Governorate")),
                    "Sales Rep Name": safe_str(row.get("Sales Rep Name")),
                    "نوع الوعد":      rule["label"],
                    "تاريخ الوعد":    row.get("Visit Date"),
                    "الاستحقاق":      row.get("Visit Date") + pd.Timedelta(days=rule["expected_days"])
                                      if pd.notnull(row.get("Visit Date")) else pd.NaT,
                    "Visit Notes":    safe_str(row.get("Visit Notes"))[:120],
                })
                break  # one promise per visit (first matching rule)

    if not records:
        return pd.DataFrame()

    p = pd.DataFrame(records)
    # keep the latest promise per customer
    p = (p.sort_values("تاريخ الوعد")
          .groupby("Customer Name", as_index=False).tail(1))

    def _evaluate(r):
        cust = r["Customer Name"]
        promise_date = r["تاريخ الوعد"]
        due = r["الاستحقاق"]
        # converted after the promise?
        conv = cur_since.get(cust)
        if latest_status.get(cust) == "Current Customer" and pd.notnull(conv) and conv >= promise_date:
            return "✅ تحول لعميل حالي"
        # a later visit happened after the promise?
        lv = last_visit.get(cust)
        if pd.notnull(lv) and lv > promise_date:
            return "🔁 تمت متابعته"
        if pd.notnull(due) and due <= today:
            return "🔥 مستحق الآن"
        return "⏳ لم يستحق بعد"

    p["حالة الوعد"] = p.apply(_evaluate, axis=1)
    p["أيام منذ الوعد"] = (today - p["تاريخ الوعد"]).dt.days
    p["الحالة الحالية"] = p["Customer Name"].map(latest_status).fillna("—")
    p = p.sort_values(["حالة الوعد", "أيام منذ الوعد"], ascending=[True, False])
    return p.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════
# 2) NEXT BEST VISIT — قائمة أولويات الزيارة
# ═══════════════════════════════════════════════════════════════════

def next_best_visits(journey_df: pd.DataFrame,
                     classified_df: pd.DataFrame,
                     promises_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Priority score per customer with Arabic reasons.
    Higher score = should be visited sooner.
    """
    if journey_df.empty:
        return pd.DataFrame()

    j = journey_df.copy()
    days = j["Days Since Last Visit"].fillna(9999)

    was_current = set(
        classified_df.loc[classified_df["Display Status"] == "Current Customer", "Customer Name"]
    ) if not classified_df.empty else set()

    overdue_promise = set()
    if promises_df is not None and not promises_df.empty:
        overdue_promise = set(
            promises_df.loc[promises_df["حالة الوعد"] == "🔥 مستحق الآن", "Customer Name"]
        )

    scores, reasons_list = [], []
    for _, r in j.iterrows():
        cust   = r["Customer Name"]
        status = safe_str(r.get("Latest Status"))
        d      = days.loc[r.name]
        score  = 0.0
        reasons = []

        if cust in overdue_promise:
            score += 35; reasons.append("وعد مستحق لم يُتابَع")
        if status == "Potential Customer":
            score += 30; reasons.append("عميل محتمل — قريب من القرار")
        if status in ("Former Customer", "Not Interested") and cust in was_current:
            score += 35; reasons.append("متسرب — كان عميلاً حالياً (إنقاذ)")
        if status == "Current Customer" and d >= 45:
            score += 30; reasons.append(f"عميل حالي بدون زيارة منذ {int(d)} يوم (خطر)")
        if status == "New Customer" and int(r.get("Visit Count", 0)) <= 1:
            score += 20; reasons.append("عميل جديد بلا زيارة ثانية")
        if status == "Target Customer":
            score += 10; reasons.append("مستهدف")
        # recency pressure (max +20 عند 180 يوم)
        score += min(float(d), 180.0) / 180.0 * 20.0

        scores.append(round(score, 1))
        reasons_list.append(" + ".join(reasons) if reasons else "زيارة دورية")

    j["أولوية الزيارة"] = scores
    j["سبب الأولوية"]   = reasons_list
    cols = ["Customer Name", "Governorate", "Sales Rep Name", "Latest Status",
            "Days Since Last Visit", "Visit Count", "أولوية الزيارة", "سبب الأولوية"]
    cols = [c for c in cols if c in j.columns]
    return (j[cols].sort_values("أولوية الزيارة", ascending=False)
            .reset_index(drop=True))


# ═══════════════════════════════════════════════════════════════════
# 3) COMPETITOR INTELLIGENCE — تحليل المنافسين من الملاحظات
# ═══════════════════════════════════════════════════════════════════

COMPETITORS = {
    "نيوهوب":      ["نيوهوب", "نيو هوب"],
    "الإيمان":     ["الايمان", "علف الايمان", "بيوكل الايمان"],
    "هيرمان":      ["هرمان", "هيرمان"],
    "BT":          ["بي تي", "شغال bt", "مع bt"],
    "مكة":         ["شغال مكه", "علف مكه"],
    "الفجر":       ["الفجر"],
    "السلام":      ["علف السلام", "شغال السلام", "بعلف السلام"],
    "المجد":       ["علف المجد", "شغال المجد", "بعلف المجد"],
    "فيدمكس":      ["فيدمكس", "فيد مكس", "فيدميكس"],
    "وادي النيل":  ["وادي النيل", "الوادي للنيل"],
    "نماء":        ["نماء"],
    "هايدا":       ["هايدا"],
    "الصلاح":      ["الصلاح"],
    "العبور":      ["العبور"],
    "القائد":      ["القائد"],
    "الشروق":      ["علف الشروق", "مع الشروق"],
    "الأهرام":     ["علف الاهرام"],
    "أبو هاشم":    ["ابو هاشم"],
    "الزعيم":      ["الزعيم"],
    "الأمانة":     ["علف الامانه"],
    "البركة":      ["علف البركه"],
    "أفريكانز":    ["افريكانز", "افريكان"],
    "كايرو ثري":   ["كايرو ثري", "كايرو تري", "كايرو ثرى"],
}
_COMP_NORM = {
    comp: [normalize_arabic(a) for a in aliases]
    for comp, aliases in COMPETITORS.items()
}


def competitor_mentions(classified_df: pd.DataFrame,
                        journey_df: pd.DataFrame) -> dict:
    """
    Scan all notes for competitor mentions.
    Returns dict: mentions (df), by_competitor, by_gov_matrix, losing_to,
                  fig_competitors, fig_matrix
    """
    out = {"mentions": pd.DataFrame(), "by_competitor": pd.DataFrame(),
           "by_gov_matrix": pd.DataFrame(), "losing_to": pd.DataFrame(),
           "fig_competitors": None}

    if classified_df.empty or "Visit Notes" not in classified_df.columns:
        return out

    latest_status = {}
    if not journey_df.empty and "Latest Status" in journey_df.columns:
        latest_status = dict(zip(journey_df["Customer Name"], journey_df["Latest Status"]))

    records = []
    df = classified_df
    notes = df["Visit Notes"].astype(str).tolist()
    for i, note in enumerate(notes):
        norm = normalize_arabic(note)
        if not norm:
            continue
        for comp, aliases in _COMP_NORM.items():
            if any(a in norm for a in aliases):
                row = df.iloc[i]
                cust = safe_str(row.get("Customer Name"))
                records.append({
                    "المنافس":        comp,
                    "Customer Name":  cust,
                    "Governorate":    safe_str(row.get("Governorate")),
                    "Sales Rep Name": safe_str(row.get("Sales Rep Name")),
                    "Visit Date":     row.get("Visit Date"),
                    "الحالة الحالية": latest_status.get(cust, "—"),
                })

    if not records:
        return out

    m = pd.DataFrame(records)
    out["mentions"] = m

    # unique customers per competitor
    by_comp = (m.groupby("المنافس")["Customer Name"].nunique()
               .reset_index(name="عدد العملاء").sort_values("عدد العملاء", ascending=True))
    out["by_competitor"] = by_comp

    # top-12 only, soft red, no axis titles — per the approved design
    top12 = by_comp.tail(12)
    fig = px.bar(top12, x="عدد العملاء", y="المنافس", orientation="h",
                 color_discrete_sequence=["#F08080"], template=PLOTLY_TEMPLATE,
                 text="عدد العملاء")
    fig.update_traces(textposition="outside", marker=dict(cornerradius=4))
    fig.update_layout(paper_bgcolor=BG, margin=dict(l=10, r=45, t=10, b=10),
                      height=360, xaxis_title="", yaxis_title="")
    out["fig_competitors"] = fig

    # competitor × governorate matrix — columns ordered by competitor size,
    # rows (governorates) ordered by total mentions, top 15
    top_comps = by_comp.sort_values("عدد العملاء", ascending=False).head(10)["المنافس"].tolist()
    mm = m[m["المنافس"].isin(top_comps)]
    matrix = mm.pivot_table(
        index="Governorate", columns="المنافس",
        values="Customer Name", aggfunc="nunique", fill_value=0,
    )
    matrix = matrix.reindex(columns=[c for c in top_comps if c in matrix.columns])
    matrix = matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index].head(15)
    out["by_gov_matrix"] = matrix

    # who are we losing to: mentioned competitor + latest status negative
    lose = (m[m["الحالة الحالية"].isin(["Not Interested", "Former Customer", "Target Customer"])]
            .drop_duplicates(subset=["Customer Name", "المنافس"])
            .sort_values(["المنافس", "Governorate"]))
    out["losing_to"] = lose.reset_index(drop=True)

    return out


# ═══════════════════════════════════════════════════════════════════
# 4) PRODUCTIVITY — إنتاجية المندوب الزمنية
# ═══════════════════════════════════════════════════════════════════

_WEEKDAYS_AR = {5: "السبت", 6: "الأحد", 0: "الاثنين", 1: "الثلاثاء",
                2: "الأربعاء", 3: "الخميس", 4: "الجمعة"}
_WEEKDAY_ORDER = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]


def weekday_productivity(classified_df: pd.DataFrame) -> dict:
    """Visits by weekday per rep: pivot matrix (design table) + stats per rep."""
    out = {"heatmap": None, "pivot": pd.DataFrame(), "stats": pd.DataFrame()}
    if classified_df.empty or "Visit Date" not in classified_df.columns:
        return out

    df = classified_df.copy()
    df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")
    df = df.dropna(subset=["Visit Date"])
    df["اليوم"] = df["Visit Date"].dt.dayofweek.map(_WEEKDAYS_AR)

    pivot = (df.pivot_table(index="Sales Rep Name", columns="اليوم",
                            values="Customer Name", aggfunc="count", fill_value=0)
             .reindex(columns=[c for c in _WEEKDAY_ORDER], fill_value=0))
    out["pivot"] = pivot

    # active days per rep
    stats = []
    for rep, g in df.groupby("Sales Rep Name"):
        active_days  = g["Visit Date"].dt.date.nunique()
        months       = g["Visit Date"].dt.to_period("M").nunique()
        stats.append({
            "Sales Rep Name":            rep,
            "أيام عمل مسجلة":            active_days,
            "متوسط أيام العمل شهرياً":   round(active_days / max(1, months), 1),
            "متوسط زيارات/يوم عمل":      round(len(g) / max(1, active_days), 1),
            "أقصى فجوة بين زيارتين (يوم)": int(g["Visit Date"].sort_values().diff().dt.days.max() or 0),
        })
    out["stats"] = (pd.DataFrame(stats)
                    .sort_values("متوسط زيارات/يوم عمل", ascending=False)
                    .reset_index(drop=True))
    return out


# ═══════════════════════════════════════════════════════════════════
# 5) DATA & NOTE QUALITY — جودة التسجيل
# ═══════════════════════════════════════════════════════════════════

def note_quality(classified_df: pd.DataFrame) -> pd.DataFrame:
    """Per-rep note quality: empty %, too-short %, avg length, copy-paste %."""
    if classified_df.empty:
        return pd.DataFrame()
    df = classified_df.copy()
    df["_note"] = df["Visit Notes"].astype(str).str.strip() if "Visit Notes" in df.columns else ""

    rows = []
    for rep, g in df.groupby("Sales Rep Name"):
        n = len(g)
        notes = g["_note"]
        empty = int((notes == "").sum() + (notes.str.lower() == "nan").sum())
        nonempty = notes[(notes != "") & (notes.str.lower() != "nan")]
        short = int((nonempty.str.len() < 15).sum())
        dup   = int(nonempty.duplicated(keep=False).sum())
        rows.append({
            "Sales Rep Name":        rep if rep else "(بدون اسم مندوب)",
            "الزيارات":              n,
            "ملاحظات فارغة %":       round(empty / n * 100, 1),
            "ملاحظات قصيرة جداً %":  round(short / max(1, len(nonempty)) * 100, 1),
            "ملاحظات منسوخة %":      round(dup / max(1, len(nonempty)) * 100, 1),
            "متوسط طول الملاحظة":    int(nonempty.str.len().mean() or 0),
        })
    return (pd.DataFrame(rows).sort_values("ملاحظات فارغة %", ascending=False)
            .reset_index(drop=True))


def data_quality_summary(classified_df: pd.DataFrame) -> dict:
    """Overall data health indicators."""
    df = classified_df
    n = max(1, len(df))
    def _missing(col):
        if col not in df.columns:
            return n
        s = df[col].astype(str).str.strip()
        return int((s == "").sum() + (s.str.lower() == "nan").sum())
    return {
        "total":         len(df),
        "no_rep":        _missing("Sales Rep Name"),
        "no_gov":        _missing("Governorate"),
        "no_note":       _missing("Visit Notes"),
        "no_date":       int(pd.to_datetime(df["Visit Date"], errors="coerce").isna().sum())
                         if "Visit Date" in df.columns else n,
        "exact_dups":    int(df.duplicated(subset=[c for c in
                            ["Visit Date", "Customer Name", "Sales Rep Name", "Visit Notes"]
                            if c in df.columns]).sum()),
    }


# ═══════════════════════════════════════════════════════════════════
# 6) ENGINE ACCURACY — دقة المحرك مقابل التصنيف اليدوي
# ═══════════════════════════════════════════════════════════════════

def engine_agreement(classified_df: pd.DataFrame) -> dict:
    """
    For manually-classified visits, re-run the engine on the note and
    compare with the human decision. Returns agreement % + confusion table.
    """
    from classification_engine import classify_note

    out = {"n": 0, "engine_blind": 0, "n_opinion": 0, "agreement": None,
           "confusion": pd.DataFrame(), "samples": pd.DataFrame()}
    if classified_df.empty or "Override Source" not in classified_df.columns:
        return out

    manual = classified_df[classified_df["Override Source"] == "Manual"]
    if manual.empty:
        return out

    preds, mismatch_rows = [], []
    for _, row in manual.iterrows():
        pred = classify_note(safe_str(row.get("Visit Notes")))["display_status"]
        human = safe_str(row.get("Display Status"))
        preds.append((human, pred))
        if pred not in ("Unclassified",) and pred != human and len(mismatch_rows) < 300:
            mismatch_rows.append({
                "Customer Name": safe_str(row.get("Customer Name")),
                "تصنيف الموظف":  human,
                "تصنيف المحرك":  pred,
                "Visit Notes":   safe_str(row.get("Visit Notes"))[:120],
            })

    cmp_df = pd.DataFrame(preds, columns=["Human", "Engine"])
    out["n"] = len(cmp_df)
    # rows the engine can't classify at all — that's exactly WHY they were
    # classified manually; they measure keyword coverage, not accuracy
    blind = cmp_df["Engine"] == "Unclassified"
    out["engine_blind"] = int(blind.sum())
    opinion = cmp_df[~blind]
    out["n_opinion"] = len(opinion)
    if len(opinion):
        out["agreement"] = round((opinion["Human"] == opinion["Engine"]).mean() * 100, 1)
        out["confusion"] = opinion.pivot_table(index="Human", columns="Engine",
                                               aggfunc=len, fill_value=0)
    out["samples"] = pd.DataFrame(mismatch_rows)
    return out


_STOP_WORDS = {normalize_arabic(w) for w in [
    "تم", "في", "من", "الى", "على", "مع", "عن", "و", "او", "ثم", "ان", "أن",
    "العميل", "عميل", "زيارة", "زياره", "اليوم", "بتاريخ", "هو", "هي", "لا",
]}


def unclassified_phrases(classified_df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    """
    Most repeated 2/3-word phrases in Unclassified or low-confidence notes —
    candidates for new keyword rules.
    """
    if classified_df.empty:
        return pd.DataFrame()
    mask = (classified_df["Display Status"] == "Unclassified")
    if "Confidence Score" in classified_df.columns:
        mask = mask | (classified_df["Confidence Score"] < 40)
    notes = classified_df.loc[mask, "Visit Notes"].astype(str)

    counter: Counter = Counter()
    for note in notes:
        words = [w for w in normalize_arabic(note).split() if len(w) > 1]
        for size in (2, 3):
            for i in range(len(words) - size + 1):
                gram = words[i:i + size]
                if all(w in _STOP_WORDS for w in gram):
                    continue
                counter[" ".join(gram)] += 1

    rows = [{"العبارة": g, "التكرار": c} for g, c in counter.most_common(top_n * 3) if c >= 3]
    return pd.DataFrame(rows[:top_n])


# ═══════════════════════════════════════════════════════════════════
# 7) PERIOD COMPARISON — مقارنة الشهر الحالي بالسابق
# ═══════════════════════════════════════════════════════════════════

def period_comparison(classified_df: pd.DataFrame, transitions_df: pd.DataFrame) -> dict:
    """
    Compare the latest data month with the month before it.
    Returns {"cur_label", "prev_label", "metrics": [(label, cur, prev), ...]}
    """
    out = {"cur_label": "", "prev_label": "", "metrics": []}
    if classified_df.empty or "Visit Date" not in classified_df.columns:
        return out

    d = pd.to_datetime(classified_df["Visit Date"], errors="coerce")
    if d.dropna().empty:
        return out
    cur_p  = d.max().to_period("M")
    prev_p = cur_p - 1
    cur  = classified_df[d.dt.to_period("M") == cur_p]
    prev = classified_df[d.dt.to_period("M") == prev_p]

    # first-ever visits (new relationships) per month
    first_visit = classified_df.assign(_d=d).groupby("Customer Name")["_d"].min()

    def _conv_in(p):
        if transitions_df is None or transitions_df.empty:
            return 0
        td = pd.to_datetime(transitions_df["Transition Date"], errors="coerce")
        return int(((transitions_df["To Status"] == "Current Customer")
                    & (td.dt.to_period("M") == p)).sum())

    def _m(df_p, p):
        dd = pd.to_datetime(df_p["Visit Date"], errors="coerce")
        return {
            "الزيارات":            len(df_p),
            "عملاء تمت زيارتهم":   df_p["Customer Name"].nunique(),
            "عملاء جدد (أول زيارة)": int((first_visit.dt.to_period("M") == p).sum()),
            "تحويلات لعميل حالي":  _conv_in(p),
            "زيارات لم تتم":        int((df_p["Display Status"] == "No Meeting").sum()),
            "مندوبون نشطون":       df_p["Sales Rep Name"].replace("", np.nan).nunique(),
            "أيام عمل":            dd.dt.date.nunique(),
        }

    mc, mp = _m(cur, cur_p), _m(prev, prev_p)
    out["cur_label"]  = str(cur_p)
    out["prev_label"] = str(prev_p)
    out["metrics"] = [(k, mc[k], mp[k]) for k in mc]
    return out


# ═══════════════════════════════════════════════════════════════════
# 8) COVERAGE MAP — خريطة تغطية المحافظات (تعمل أوفلاين)
# ═══════════════════════════════════════════════════════════════════

# Approximate centroids (lat, lon) — keys are normalized governorate names
_GOV_CENTROIDS = {
    "القاهره": (30.05, 31.25),  "الجيزه": (29.85, 31.10),   "الاسكندريه": (31.20, 29.92),
    "البحيره": (30.90, 30.45),  "الغربيه": (30.87, 31.03),  "كفر الشيخ": (31.30, 30.80),
    "الدقهليه": (31.05, 31.38), "دمياط": (31.42, 31.81),    "الشرقيه": (30.70, 31.63),
    "المنوفيه": (30.55, 30.99), "القليوبيه": (30.25, 31.21),"بورسعيد": (31.26, 32.30),
    "الاسماعيليه": (30.60, 32.27), "السويس": (29.97, 32.55),"شمال سيناء": (30.60, 33.80),
    "جنوب سيناء": (28.50, 33.90), "الفيوم": (29.30, 30.84), "بني سويف": (29.07, 31.10),
    "المنيا": (28.10, 30.75),   "اسيوط": (27.18, 31.18),    "سوهاج": (26.55, 31.70),
    "قنا": (26.16, 32.72),      "الاقصر": (25.70, 32.65),   "اسوان": (24.09, 32.90),
    "البحر الاحمر": (26.70, 33.90), "الوادي الجديد": (25.40, 29.00), "مطروح": (31.35, 27.25),
    # common non-standard entries in the visits data
    "العاشر من رمضان": (30.31, 31.75), "سيناء": (29.50, 33.80),
}


def coverage_map(classified_df: pd.DataFrame, journey_df: pd.DataFrame) -> dict:
    """Bubble map of governorates: size = customers, color = % Current."""
    out = {"fig": None, "unmatched": [], "table": pd.DataFrame()}
    if classified_df.empty or "Governorate" not in classified_df.columns:
        return out

    latest = journey_df[["Customer Name", "Latest Status", "Governorate"]].copy() \
        if not journey_df.empty else pd.DataFrame()
    if latest.empty:
        return out

    g = latest.groupby("Governorate").agg(
        العملاء=("Customer Name", "nunique"),
        الحاليون=("Latest Status", lambda s: int((s == "Current Customer").sum())),
    ).reset_index()
    g["نسبة الحاليين %"] = (g["الحاليون"] / g["العملاء"] * 100).round(1)

    lats, lons, matched = [], [], []
    unmatched = []
    for _, r in g.iterrows():
        key = normalize_arabic(safe_str(r["Governorate"]))
        if key in _GOV_CENTROIDS:
            lat, lon = _GOV_CENTROIDS[key]
            lats.append(lat); lons.append(lon); matched.append(True)
        else:
            lats.append(None); lons.append(None); matched.append(False)
            if r["Governorate"]:
                unmatched.append(safe_str(r["Governorate"]))
    g["_lat"], g["_lon"] = lats, lons
    out["unmatched"] = unmatched
    out["table"] = g.drop(columns=["_lat", "_lon"]).sort_values("العملاء", ascending=False)

    gm = g.dropna(subset=["_lat"])
    if gm.empty:
        return out

    fig = px.scatter(
        gm, x="_lon", y="_lat", size="العملاء", color="نسبة الحاليين %",
        color_continuous_scale=[[0, "#C00000"], [0.5, "#FFC000"], [1, "#70AD47"]],
        size_max=55, text="Governorate", template=PLOTLY_TEMPLATE,
        hover_name="Governorate",
        hover_data={"_lat": False, "_lon": False, "العملاء": True,
                    "الحاليون": True, "نسبة الحاليين %": True},
        title="خريطة التغطية — حجم الدائرة = عدد العملاء، اللون = نسبة العملاء الحاليين",
    )
    fig.update_traces(textposition="top center", textfont_size=11)
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="", showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(title="", showgrid=False, zeroline=False, showticklabels=False,
                   scaleanchor="x", scaleratio=1),
        height=650, margin=dict(l=10, r=10, t=60, b=10),
    )
    out["fig"] = fig
    return out


# ═══════════════════════════════════════════════════════════════════
# 9) RETENTION — معدل بقاء العملاء المحوّلين
# ═══════════════════════════════════════════════════════════════════

def conversion_retention(conversions_df: pd.DataFrame,
                         journey_df: pd.DataFrame) -> dict:
    """Of customers who converted to Current, how many are still Current?"""
    out = {"n_converted": 0, "still_current": 0, "retention_pct": None,
           "lost_after_conversion": pd.DataFrame()}
    if conversions_df is None or conversions_df.empty or journey_df.empty:
        return out

    latest = dict(zip(journey_df["Customer Name"], journey_df["Latest Status"]))
    conv = conversions_df.copy()
    conv["الحالة الحالية"] = conv["Customer Name"].map(latest)

    out["n_converted"]  = len(conv)
    out["still_current"] = int((conv["الحالة الحالية"] == "Current Customer").sum())
    out["retention_pct"] = round(out["still_current"] / max(1, out["n_converted"]) * 100, 1)

    lost = conv[conv["الحالة الحالية"].isin(["Former Customer", "Not Interested"])]
    keep_cols = [c for c in ["Customer Name", "Sales Rep Name", "Governorate",
                             "Transition Date", "الحالة الحالية"] if c in lost.columns]
    out["lost_after_conversion"] = lost[keep_cols].reset_index(drop=True)
    return out


# ═══════════════════════════════════════════════════════════════════
# 10) SALES-REP REPORT — كل بيانات تقرير المندوب لفترة محددة
# ═══════════════════════════════════════════════════════════════════

WASTED_STATUSES = ["Not Interested", "Former Customer"]
_MONTHS_AR = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
              7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}


def canonical_governorates(series: pd.Series) -> dict:
    """
    Map every spelling of a governorate to the most common one
    ("البحيره" و"البحيرة" يظهران كمحافظة واحدة).
    """
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    if s.empty:
        return {}
    tmp = pd.DataFrame({"raw": s, "key": s.map(normalize_arabic)})
    best = (tmp.groupby(["key", "raw"]).size().reset_index(name="n")
              .sort_values("n", ascending=False).drop_duplicates("key"))
    key_to_name = dict(zip(best["key"], best["raw"]))
    return {raw: key_to_name[normalize_arabic(raw)] for raw in s.unique()}


def rep_report_data(classified_df: pd.DataFrame, journey_df: pd.DataFrame,
                    rep: str, year: int, month=None) -> dict:
    """
    Everything the per-rep Excel report needs.
    year = required, month = None means the whole year.
    Period figures come with two references: the previous period and the team
    average, because a bare number can't be judged on its own.
    """
    out = {}
    df = classified_df.copy()
    df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")
    df = df.dropna(subset=["Visit Date"])

    gov_map = canonical_governorates(df["Governorate"]) if "Governorate" in df.columns else {}
    df["_gov"] = df["Governorate"].map(lambda g: gov_map.get(str(g).strip(), str(g).strip())) \
        if "Governorate" in df.columns else ""

    rep_all = df[df["Sales Rep Name"] == rep]

    def _slice(frame, y, m):
        f = frame[frame["Visit Date"].dt.year == y]
        return f if m is None else f[f["Visit Date"].dt.month == m]

    per = _slice(rep_all, year, month)
    if month is None:
        prev, prev_label = _slice(rep_all, year - 1, None), f"{year - 1}"
        period_label = f"سنة {year}"
    else:
        py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
        prev, prev_label = _slice(rep_all, py, pm), f"{_MONTHS_AR[pm]} {py}"
        period_label = f"{_MONTHS_AR[month]} {year}"

    team_per = _slice(df[df["Sales Rep Name"].astype(str).str.strip() != ""], year, month)

    # ── header ──
    # "المحافظات المسؤول عنها" = كل محافظات زياراته (نطاقه)، لا محافظات الفترة
    # فقط — حتى تتسق مع شيت المنافسين. توزيع الفترة يظهر في جدول منفصل.
    territory = rep_all["_gov"].value_counts()
    in_period = per["_gov"].value_counts() if len(per) else pd.Series(dtype=int)
    out["header"] = {
        "rep": rep, "period": period_label, "prev_label": prev_label,
        "governorates": " · ".join(territory.index.tolist()),
        "governorates_period": " · ".join(in_period.index.tolist()) if len(in_period) else "—",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # ── transitions & conversions (rep-attributed) ──
    from dashboard import customer_transitions
    trans = customer_transitions(classified_df)
    rep_trans = trans[trans["Sales Rep Name"] == rep].copy() if not trans.empty else pd.DataFrame()
    if not rep_trans.empty:
        rep_trans["Transition Date"] = pd.to_datetime(rep_trans["Transition Date"], errors="coerce")
    conv_all = rep_trans[rep_trans["To Status"] == "Current Customer"] if not rep_trans.empty else pd.DataFrame()
    conv_per = (conv_all[(conv_all["Transition Date"].dt.year == year) &
                         ((month is None) | (conv_all["Transition Date"].dt.month == month))]
                if not conv_all.empty else pd.DataFrame())

    def _conv_count(frame, y, m):
        if trans.empty:
            return 0
        t = trans[trans["To Status"] == "Current Customer"].copy()
        t["Transition Date"] = pd.to_datetime(t["Transition Date"], errors="coerce")
        t = t[(t["Transition Date"].dt.year == y) & ((m is None) | (t["Transition Date"].dt.month == m))]
        return len(t[t["Sales Rep Name"] == rep]) if frame is None else t

    # ── KPI block with the two references ──
    def _kpis(frame):
        if frame.empty:
            return dict(visits=0, customers=0, workdays=0, per_day=0.0, wasted=0, nomeet=0)
        wd = frame["Visit Date"].dt.date.nunique()
        return dict(
            visits=len(frame), customers=frame["Customer Name"].nunique(), workdays=wd,
            per_day=round(len(frame) / max(1, wd), 1),
            wasted=int(frame["Display Status"].isin(WASTED_STATUSES).sum()),
            nomeet=int((frame["Display Status"] == "No Meeting").sum()),
        )

    k_now, k_prev = _kpis(per), _kpis(prev)
    n_reps = max(1, team_per["Sales Rep Name"].nunique())
    team_avg = dict(
        visits=round(len(team_per) / n_reps, 1),
        customers=round(team_per.groupby("Sales Rep Name")["Customer Name"].nunique().mean(), 1) if len(team_per) else 0,
        workdays=round(team_per.groupby("Sales Rep Name")["Visit Date"].apply(lambda s: s.dt.date.nunique()).mean(), 1) if len(team_per) else 0,
    )
    conv_prev = _conv_count(None, year - 1, None) if month is None else _conv_count(None, *( (year - 1, 12) if month == 1 else (year, month - 1)))
    team_conv = _conv_count(True, year, month)
    team_conv_avg = round(len(team_conv) / n_reps, 1) if isinstance(team_conv, pd.DataFrame) and len(team_conv) else 0

    pct = lambda a, b: f"{a / b * 100:.1f}%" if b else "—"
    out["kpis"] = pd.DataFrame([
        ["إجمالي الزيارات",       k_now["visits"],    k_prev["visits"],    team_avg["visits"]],
        ["عملاء تمت زيارتهم",     k_now["customers"], k_prev["customers"], team_avg["customers"]],
        ["أيام عمل فعلية",        k_now["workdays"],  k_prev["workdays"],  team_avg["workdays"]],
        ["متوسط زيارات/يوم عمل",  k_now["per_day"],   k_prev["per_day"],   ""],
        ["تحويلات إلى عميل حالي", len(conv_per),      conv_prev,           team_conv_avg],
        ["زيارات لغير مهتم/متوقف", k_now["wasted"],   k_prev["wasted"],    ""],
        ["زيارات لم تتم (غائب/مسافر)", k_now["nomeet"], k_prev["nomeet"],  ""],
    ], columns=["المؤشر", "الفترة الحالية", "الفترة السابقة", "متوسط الفريق"])
    out["ratios"] = pd.DataFrame([
        ["نسبة الزيارات غير المنتجة", pct(k_now["wasted"], k_now["visits"])],
        ["نسبة الزيارات التي لم تتم", pct(k_now["nomeet"], k_now["visits"])],
        ["نسبة الزيارات المنتجة",
         pct(k_now["visits"] - k_now["wasted"] - k_now["nomeet"], k_now["visits"])],
        ["تحويلات تراكمية (كل تاريخ المندوب)", len(conv_all)],
    ], columns=["المؤشر", "القيمة"])
    status_map = dict(zip(journey_df["Customer Name"], journey_df["Latest Status"])) \
        if not journey_df.empty else {}
    days_map = dict(zip(journey_df["Customer Name"], journey_df["Days Since Last Visit"])) \
        if not journey_df.empty else {}

    # ── 1) الزيارات: شهري / أسبوعي / يومي + أيام الأسبوع ──
    if len(per):
        mon = (per.assign(m=per["Visit Date"].dt.to_period("M").astype(str))
                 .groupby("m").agg(الزيارات=("Customer Name", "size"),
                                   العملاء=("Customer Name", "nunique"),
                                   أيام_عمل=("Visit Date", lambda s: s.dt.date.nunique()))
                 .reset_index().rename(columns={"m": "الشهر", "أيام_عمل": "أيام عمل"}))
        wk = (per.assign(w=per["Visit Date"].dt.to_period("W").apply(lambda p: p.start_time.strftime("%Y-%m-%d")))
                .groupby("w").agg(الزيارات=("Customer Name", "size"),
                                  العملاء=("Customer Name", "nunique"))
                .reset_index().rename(columns={"w": "الأسبوع (يبدأ)"}))
        day = (per.assign(d=per["Visit Date"].dt.strftime("%Y-%m-%d"))
                 .groupby("d").agg(الزيارات=("Customer Name", "size"),
                                   العملاء=("Customer Name", "nunique"))
                 .reset_index().rename(columns={"d": "اليوم"}))
        wd = (per.assign(dw=per["Visit Date"].dt.dayofweek.map(_WEEKDAYS_AR))
                .groupby("dw").size().reindex(_WEEKDAY_ORDER).fillna(0).astype(int)
                .reset_index().rename(columns={"dw": "اليوم", 0: "الزيارات"}))
        wd.columns = ["اليوم", "الزيارات"]
    else:
        mon = wk = day = wd = pd.DataFrame()
    out["visits_monthly"], out["visits_weekly"] = mon, wk
    out["visits_daily"], out["visits_weekday"] = day, wd

    # ── 2) زيارات غير المهتمين والمتوقفين ──
    wasted = per[per["Display Status"].isin(WASTED_STATUSES)] if len(per) else pd.DataFrame()
    if len(wasted):
        summ = (wasted.groupby("Display Status")
                .agg(الزيارات=("Customer Name", "size"), العملاء=("Customer Name", "nunique"))
                .reset_index().rename(columns={"Display Status": "الحالة"}))
        summ["معدل تكرار الزيارة للعميل"] = (summ["الزيارات"] / summ["العملاء"]).round(2)
        summ["% من زيارات الفترة"] = (summ["الزيارات"] / len(per) * 100).round(1)
        total = pd.DataFrame([["الإجمالي", len(wasted), wasted["Customer Name"].nunique(),
                               round(len(wasted) / max(1, wasted["Customer Name"].nunique()), 2),
                               round(len(wasted) / len(per) * 100, 1)]], columns=summ.columns)
        out["wasted_summary"] = pd.concat([summ, total], ignore_index=True)
        det = wasted.copy()
        det["التاريخ"] = det["Visit Date"].dt.strftime("%Y-%m-%d")
        rep_counts = wasted.groupby("Customer Name").size()
        det["زيارات هذا العميل بالفترة"] = det["Customer Name"].map(rep_counts)
        out["wasted_detail"] = det[["التاريخ", "Customer Name", "Display Status", "_gov",
                                    "زيارات هذا العميل بالفترة", "Visit Notes"]].rename(
            columns={"Customer Name": "العميل", "Display Status": "الحالة",
                     "_gov": "المحافظة", "Visit Notes": "الملاحظة"}).sort_values("التاريخ")
    else:
        out["wasted_summary"] = out["wasted_detail"] = pd.DataFrame()

    # ── 3) التحويلات إلى عميل حالي ──
    first_visit = dict(zip(journey_df["Customer Name"], journey_df["First Visit Date"])) \
        if not journey_df.empty else {}
    def _conv_table(frame):
        if frame is None or frame.empty:
            return pd.DataFrame()
        t = frame.copy()
        t["تاريخ التحوّل"] = pd.to_datetime(t["Transition Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        t["أيام حتى التحويل"] = [
            (pd.to_datetime(d) - pd.to_datetime(first_visit.get(c))).days
            if first_visit.get(c) is not None and pd.notnull(first_visit.get(c)) else None
            for c, d in zip(t["Customer Name"], t["Transition Date"])]
        t["الحالة الحالية"] = t["Customer Name"].map(status_map)
        return t[["Customer Name", "From Status", "تاريخ التحوّل", "أيام حتى التحويل",
                  "الحالة الحالية", "Governorate"]].rename(
            columns={"Customer Name": "العميل", "From Status": "الحالة السابقة",
                     "Governorate": "المحافظة"}).sort_values("تاريخ التحوّل")
    out["conv_detail_period"] = _conv_table(conv_per)
    out["conv_detail_all"] = _conv_table(conv_all)
    avg_days = out["conv_detail_period"]["أيام حتى التحويل"].dropna().mean() if len(out["conv_detail_period"]) else None
    avg_all = out["conv_detail_all"]["أيام حتى التحويل"].dropna().mean() if len(out["conv_detail_all"]) else None
    out["conv_summary"] = pd.DataFrame([
        ["تحويلات في الفترة", len(conv_per), f"{avg_days:.0f} يوم" if pd.notnull(avg_days) else "—"],
        ["تحويلات تراكمية (كل تاريخ المندوب)", len(conv_all), f"{avg_all:.0f} يوم" if pd.notnull(avg_all) else "—"],
        ["ما زالوا عملاء حاليين الآن",
         int(sum(1 for c in conv_all["Customer Name"] if status_map.get(c) == "Current Customer")) if len(conv_all) else 0, ""],
    ], columns=["البند", "العدد", "متوسط أيام التحويل"])

    # ── 4) أكثر العملاء زيارة (الفترة + تراكمي) ──
    if len(per):
        cum = rep_all.groupby("Customer Name").size()
        top = (per.groupby("Customer Name")
               .agg(زيارات_الفترة=("Visit Date", "size"),
                    آخر_زيارة=("Visit Date", "max"), المحافظة=("_gov", "last"))
               .reset_index())
        top["زيارات تراكمية مع المندوب"] = top["Customer Name"].map(cum)
        top["الحالة الحالية"] = top["Customer Name"].map(status_map)
        top["أيام منذ آخر زيارة"] = top["Customer Name"].map(days_map)
        top["آخر_زيارة"] = top["آخر_زيارة"].dt.strftime("%Y-%m-%d")
        out["top_customers"] = (top.sort_values(["زيارات_الفترة", "زيارات تراكمية مع المندوب"],
                                                ascending=False).head(30)
                                .rename(columns={"Customer Name": "العميل",
                                                 "زيارات_الفترة": "زيارات الفترة",
                                                 "آخر_زيارة": "آخر زيارة"}))
        sd = per["Display Status"].value_counts().reset_index()
        sd.columns = ["الحالة", "الزيارات"]
        out["status_mix"] = sd
    else:
        out["top_customers"] = out["status_mix"] = pd.DataFrame()

    # ── 5) الوعود (كل تاريخ المندوب — غير مقيدة بالفترة) ──
    pr = extract_promises(classified_df, journey_df)
    if not pr.empty:
        pr = pr[pr["Sales Rep Name"] == rep].copy()
    if not pr.empty:
        pr["تاريخ الوعد"] = pd.to_datetime(pr["تاريخ الوعد"], errors="coerce").dt.strftime("%Y-%m-%d")
        pr["الاستحقاق"] = pd.to_datetime(pr["الاستحقاق"], errors="coerce").dt.strftime("%Y-%m-%d")
        out["promises"] = pr[["Customer Name", "نوع الوعد", "تاريخ الوعد", "الاستحقاق",
                              "حالة الوعد", "الحالة الحالية", "Governorate"]].rename(
            columns={"Customer Name": "العميل", "Governorate": "المحافظة"})
        out["promises_summary"] = (pr["حالة الوعد"].value_counts().reset_index()
                                   .set_axis(["حالة الوعد", "العدد"], axis=1))
    else:
        out["promises"] = out["promises_summary"] = pd.DataFrame()

    # ── 6) المنافسون في محافظات المندوب ──
    comp = competitor_mentions(classified_df, journey_df)
    men = comp["mentions"]
    rep_govs = set(rep_all["_gov"].unique())
    if not men.empty:
        men = men.copy()
        men["_gov"] = men["Governorate"].map(lambda g: gov_map.get(str(g).strip(), str(g).strip()))
        men = men[men["_gov"].isin(rep_govs)]
    if not men.empty:
        md = pd.to_datetime(men["Visit Date"], errors="coerce")
        in_per = (md.dt.year == year) & ((month is None) | (md.dt.month == month))
        summ = (men.groupby("المنافس")
                .agg(عدد_العملاء=("Customer Name", "nunique"), إشارات=("Customer Name", "size"))
                .reset_index())
        summ["ذُكر في الفترة"] = summ["المنافس"].map(men[in_per].groupby("المنافس").size()).fillna(0).astype(int)
        out["competitors"] = summ.sort_values("عدد_العملاء", ascending=False).rename(
            columns={"عدد_العملاء": "عدد العملاء"})
        out["competitor_matrix"] = men.pivot_table(index="_gov", columns="المنافس",
                                                   values="Customer Name", aggfunc="nunique",
                                                   fill_value=0).reset_index().rename(columns={"_gov": "المحافظة"})
        lose = men[men["الحالة الحالية"].isin(["Not Interested", "Former Customer", "Target Customer"])]
        out["competitor_losing"] = (lose.drop_duplicates(["Customer Name", "المنافس"])
                                    [["المنافس", "Customer Name", "الحالة الحالية", "_gov"]]
                                    .rename(columns={"Customer Name": "العميل", "_gov": "المحافظة"})
                                    .sort_values("المنافس").head(200))
    else:
        out["competitors"] = out["competitor_matrix"] = out["competitor_losing"] = pd.DataFrame()

    # ── 7) عملاء مهملون من محفظة المندوب ──
    portfolio = rep_all["Customer Name"].unique()
    if len(portfolio) and not journey_df.empty:
        neg = journey_df[journey_df["Customer Name"].isin(portfolio)].copy()
        neg["Days Since Last Visit"] = pd.to_numeric(neg["Days Since Last Visit"], errors="coerce")
        buckets = [(30, 60), (60, 90), (90, 9999)]
        rows = [["30-59 يوم", int(((neg["Days Since Last Visit"] >= 30) & (neg["Days Since Last Visit"] < 60)).sum())],
                ["60-89 يوم", int(((neg["Days Since Last Visit"] >= 60) & (neg["Days Since Last Visit"] < 90)).sum())],
                ["90+ يوم",   int((neg["Days Since Last Visit"] >= 90).sum())]]
        out["neglected_summary"] = pd.DataFrame(rows, columns=["الفئة", "عدد العملاء"])
        det = neg[neg["Days Since Last Visit"] >= 30].sort_values("Days Since Last Visit", ascending=False)
        det["Last Visit Date"] = pd.to_datetime(det["Last Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        out["neglected_detail"] = det[["Customer Name", "Latest Status", "Days Since Last Visit",
                                       "Last Visit Date", "Visit Count", "Governorate"]].rename(
            columns={"Customer Name": "العميل", "Latest Status": "الحالة", "Visit Count": "إجمالي الزيارات",
                     "Days Since Last Visit": "أيام منذ آخر زيارة", "Last Visit Date": "آخر زيارة",
                     "Governorate": "المحافظة"}).head(300)
    else:
        out["neglected_summary"] = out["neglected_detail"] = pd.DataFrame()

    # ── 8) جودة الأداء والتسجيل ──
    nomeet = per[per["Display Status"] == "No Meeting"] if len(per) else pd.DataFrame()
    if len(nomeet):
        nm = nomeet.copy(); nm["التاريخ"] = nm["Visit Date"].dt.strftime("%Y-%m-%d")
        out["nomeeting_detail"] = nm[["التاريخ", "Customer Name", "_gov", "Visit Notes"]].rename(
            columns={"Customer Name": "العميل", "_gov": "المحافظة", "Visit Notes": "الملاحظة"})
    else:
        out["nomeeting_detail"] = pd.DataFrame()

    if not rep_trans.empty:
        mv = rep_trans[(rep_trans["Transition Date"].dt.year == year) &
                       ((month is None) | (rep_trans["Transition Date"].dt.month == month))]
        out["portfolio_moves"] = (mv.groupby(["From Status", "To Status"]).size()
                                  .reset_index(name="عدد العملاء")
                                  .rename(columns={"From Status": "من", "To Status": "إلى"})
                                  .sort_values("عدد العملاء", ascending=False)) if len(mv) else pd.DataFrame()
    else:
        out["portfolio_moves"] = pd.DataFrame()

    nq = note_quality(per) if len(per) else pd.DataFrame()
    out["note_quality"] = nq[nq["Sales Rep Name"] == rep] if len(nq) else pd.DataFrame()

    if len(per):
        dup = (per.groupby(["Customer Name", per["Visit Date"].dt.strftime("%Y-%m-%d")])
               .size().reset_index(name="عدد الزيارات"))
        dup.columns = ["العميل", "التاريخ", "عدد الزيارات"]
        out["same_day_dupes"] = dup[dup["عدد الزيارات"] > 1].sort_values("عدد الزيارات", ascending=False)
        geo = (per.groupby("_gov").agg(الزيارات=("Customer Name", "size"),
                                       العملاء=("Customer Name", "nunique")).reset_index()
               .rename(columns={"_gov": "المحافظة"}).sort_values("الزيارات", ascending=False))
        out["geo_distribution"] = geo
    else:
        out["same_day_dupes"] = out["geo_distribution"] = pd.DataFrame()

    return out
