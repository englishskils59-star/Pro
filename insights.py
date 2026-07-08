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

PRIMARY   = "#1F4E79"
SECONDARY = "#2E75B6"
ACCENT    = "#70AD47"
BG        = "#F5F7FA"
PLOTLY_TEMPLATE = "plotly_white"


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

    fig = px.bar(by_comp, x="عدد العملاء", y="المنافس", orientation="h",
                 color_discrete_sequence=["#C00000"], template=PLOTLY_TEMPLATE,
                 title="عملاء مرتبطون بكل منافس (من ملاحظات الزيارات)", text="عدد العملاء")
    fig.update_traces(textposition="outside")
    fig.update_layout(paper_bgcolor=BG, margin=dict(l=20, r=40, t=50, b=20),
                      height=max(400, 24 * len(by_comp)))
    out["fig_competitors"] = fig

    # competitor × governorate matrix (top 10 competitors)
    top_comps = by_comp.sort_values("عدد العملاء", ascending=False).head(10)["المنافس"]
    mm = m[m["المنافس"].isin(top_comps)]
    out["by_gov_matrix"] = mm.pivot_table(
        index="Governorate", columns="المنافس",
        values="Customer Name", aggfunc="nunique", fill_value=0,
    )

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
    """Visits by weekday per rep (heatmap) + active-days stats per rep."""
    out = {"heatmap": None, "stats": pd.DataFrame()}
    if classified_df.empty or "Visit Date" not in classified_df.columns:
        return out

    df = classified_df.copy()
    df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")
    df = df.dropna(subset=["Visit Date"])
    df["اليوم"] = df["Visit Date"].dt.dayofweek.map(_WEEKDAYS_AR)

    pivot = (df.pivot_table(index="Sales Rep Name", columns="اليوم",
                            values="Customer Name", aggfunc="count", fill_value=0)
             .reindex(columns=[c for c in _WEEKDAY_ORDER], fill_value=0))

    fig = px.imshow(pivot, text_auto=True, aspect="auto",
                    color_continuous_scale=[[0, "#EBF3FB"], [1, PRIMARY]],
                    title="توزيع الزيارات على أيام الأسبوع لكل مندوب")
    fig.update_layout(paper_bgcolor=BG, template=PLOTLY_TEMPLATE,
                      margin=dict(l=20, r=20, t=50, b=20),
                      height=max(400, 32 * len(pivot)))
    out["heatmap"] = fig

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
        paper_bgcolor=BG, plot_bgcolor="#FFFFFF",
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
