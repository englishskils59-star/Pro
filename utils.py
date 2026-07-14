# utils.py
# WDI Visit Analytics Engine
# Utility functions: Arabic text handling, column validation, shared helpers

import pandas as pd
import numpy as np
from datetime import datetime, date
import re

# ─────────────────────────────────────────────
# REQUIRED COLUMNS
# ─────────────────────────────────────────────

REQUIRED_COLUMNS = [
    "Year", "Month", "Visit Date", "Customer Name", "Customer Category",
    "Governorate", "District", "Visit Notes", "Total Visit Flag",
    "Unique Customer Flag", "Sales Rep Name", "Current Customer",
    "Target Customer", "Potential Customer", "New Customer",
    "Not Interested Customer", "Former Customer",
]

# ─────────────────────────────────────────────
# COLUMN ALIASES
# ─────────────────────────────────────────────

COLUMN_ALIASES = {
    "السنة": "Year", "الشهر": "Month", "تاريخ الزيارة": "Visit Date",
    "اسم العميل": "Customer Name", "فئة العميل": "Customer Category",
    "المحافظة": "Governorate", "المنطقة": "District",
    "ملاحظات الزيارة": "Visit Notes", "إجمالي الزيارات": "Total Visit Flag",
    "عميل فريد": "Unique Customer Flag", "اسم المندوب": "Sales Rep Name",
    "عميل حالي": "Current Customer", "عميل مستهدف": "Target Customer",
    "عميل محتمل": "Potential Customer", "عميل جديد": "New Customer",
    "غير مهتم": "Not Interested Customer", "عميل سابق": "Former Customer",
}

# ─────────────────────────────────────────────
# STATUS LABELS & COLORS
# ─────────────────────────────────────────────

STATUS_LABELS = {
    "current": "Current Customer", "potential": "Potential Customer",
    "target": "Target Customer", "new": "New Customer",
    "former": "Former Customer", "not_interested": "Not Interested",
    "no_meeting": "No Meeting", "unclassified": "Unclassified",
}

STATUS_COLORS = {
    "Current Customer":   "#70AD47",
    "Potential Customer": "#2E75B6",
    "Target Customer":    "#FFC000",
    "New Customer":       "#1F4E79",
    "Former Customer":    "#A9A9A9",
    "Not Interested":     "#C00000",
    "No Meeting":         "#8497B0",
    "Unclassified":       "#D9D9D9",
}

# Visit statuses that do NOT represent a real customer position —
# they must never overwrite the customer's last real classification.
NON_STATUS_LABELS = {"No Meeting", "Unclassified"}

# Arabic display names for statuses (charts, badges, matrices)
STATUS_AR = {
    "Current Customer": "عميل حالي", "Potential Customer": "محتمل",
    "Target Customer": "مستهدف", "New Customer": "جديد",
    "Former Customer": "سابق", "Not Interested": "غير مهتم",
    "No Meeting": "لم تتم المقابلة", "Unclassified": "غير مصنف",
}

# ═══════════════════════════════════════════════════════════════════
# BASIC HELPERS  (must come first — used by everything below)
# ═══════════════════════════════════════════════════════════════════

def safe_str(val) -> str:
    """Convert any value to a clean string; return empty string for NaN/None."""
    if val is None:
        return ""
    if isinstance(val, float) and np.isnan(val):
        return ""
    return str(val).strip()


def contains_arabic(text: str) -> bool:
    """Return True if text contains Arabic characters."""
    if not isinstance(text, str):
        return False
    return bool(re.search(r"[\u0600-\u06FF]", text))


# ═══════════════════════════════════════════════════════════════════
# ARABIC TEXT NORMALIZATION
# ═══════════════════════════════════════════════════════════════════

# Pre-compiled regex patterns for performance
_RE_TATWEEL    = re.compile(r"ـ")
_RE_TASHKEEL   = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]"
)
_RE_ALEF       = re.compile(r"[إأآٱ]")
_RE_TA_MARBUTA = re.compile(r"ة")
_RE_YA         = re.compile(r"[يى]")
_RE_WAW        = re.compile(r"ؤ")
_RE_YA2        = re.compile(r"ئ")
_RE_SPACES     = re.compile(r"\s+")


def normalize_arabic(text: str) -> str:
    """
    Full Arabic normalization for keyword matching:
    - Remove Tatweel (kashida ـ)
    - Remove Tashkeel (diacritics)
    - Unify Alef variants  → ا
    - Unify Ta Marbuta     → ه
    - Unify Ya variants    → ي
    - Unify Waw/Ya Hamza   → و / ي
    - Collapse multiple spaces
    """
    if not isinstance(text, str):
        return ""
    text = _RE_TATWEEL.sub("", text)
    text = _RE_TASHKEEL.sub("", text)
    text = _RE_ALEF.sub("ا", text)
    text = _RE_TA_MARBUTA.sub("ه", text)
    text = _RE_YA.sub("ي", text)
    text = _RE_WAW.sub("و", text)
    text = _RE_YA2.sub("ي", text)
    text = _RE_SPACES.sub(" ", text).strip()
    return text


# ═══════════════════════════════════════════════════════════════════
# CUSTOMER NAME CLEANING
# ═══════════════════════════════════════════════════════════════════

# Pattern: "ا/ ", "م/ ", "د/ ", "أ/ " etc. at start of name
_RE_SLASH_PREFIX = re.compile(r"^[اأإآمدهعأ]\s*/\s*")

# Pattern: handle "ا/احمد" with no space after slash
_RE_SLASH_PREFIX2 = re.compile(r"^[\w]{1}\s*/\s*")

_NAME_PREFIXES = [
    # titles
    "الاستاذ", "الأستاذ", "المهندس", "الدكتور", "الدكتوره",
    "الحاج", "الحاجه", "الحاجة", "الشيخ", "السيد", "السيده",
    "الانسه", "الآنسة", "استاذ", "أستاذ", "مهندس", "دكتور",
    "دكتوره", "حاج", "حاجه", "شيخ", "اللواء", "العميد",
    # business types
    "مزرعه", "مزرعة", "مزارع", "شركه", "شركة", "مؤسسه",
    "مؤسسة", "محل", "محلات", "مصنع", "مجمع", "مجموعه", "مجموعة",
    "مندوب", "صاحب", "موزع",
]

_NAME_SUFFIXES = [
    "للدواجن", "للتجاره", "للتجارة", "للانتاج", "للإنتاج",
    "للتسمين", "للبيض", "دواجن", "بروميل", "فروج",
    "تاجر", "وكيل", "فرع",
]

# Normalize all prefixes/suffixes once at import
_NORM_PREFIXES = [normalize_arabic(p) for p in _NAME_PREFIXES]
_NORM_SUFFIXES = [normalize_arabic(s) for s in _NAME_SUFFIXES]

_RE_PUNCT_START = re.compile(r"^[\-–/\\()\[\]،,\.\s]+")
_RE_PUNCT_END   = re.compile(r"[\-–/\\()\[\]،,\.\s]+$")
_RE_DIGITS      = re.compile(r"\b\d{1,3}\b")


def clean_customer_name(name: str) -> str:
    """
    Clean and normalize a customer name for deduplication.

    What gets removed:
    ┌─────────────────────────────────────────────────────┐
    │  ا/ اسلام      →  اسلام                            │
    │  م/ كريم يوسف  →  كريم يوسف                       │
    │  الحاج محمود   →  محمود                            │
    │  مزرعة أحمد    →  احمد                             │
    │  شركة السلام للدواجن  →  السلام                   │
    │  أحمد / إبراهيم →  احمد / ابراهيم (normalized)   │
    └─────────────────────────────────────────────────────┘

    Returns cleaned + normalized name.
    Original name is preserved in 'Customer Name' column.
    Cleaned name goes into 'Customer Name Cleaned' column.
    """
    if not isinstance(name, str) or not name.strip():
        return ""

    text = safe_str(name)

    # ── 1. Full Arabic normalization ──
    text = normalize_arabic(text)

    # ── 2. Remove slash-style prefix: "ا/ " "م/ " "د/ " etc. ──
    #    Covers: "ا/ احمد", "ا/احمد", "م / كريم"
    text = re.sub(r"^[اأإآمدهعأبتث]\s*/\s*", "", text).strip()

    # ── 3. Remove title / business prefixes ──
    changed = True
    while changed:
        changed = False
        text = text.strip()
        for prefix_norm in _NORM_PREFIXES:
            if text.startswith(prefix_norm + " ") or text == prefix_norm:
                text = text[len(prefix_norm):].strip()
                changed = True
            elif text.startswith(prefix_norm):
                text = text[len(prefix_norm):].strip()
                changed = True

    # ── 4. Remove trailing suffixes ──
    for suffix_norm in _NORM_SUFFIXES:
        if text.endswith(" " + suffix_norm):
            text = text[: -(len(suffix_norm) + 1)].strip()
        elif text.endswith(suffix_norm) and len(text) > len(suffix_norm):
            text = text[: -len(suffix_norm)].strip()

    # ── 5. Clean leading / trailing punctuation ──
    text = _RE_PUNCT_START.sub("", text)
    text = _RE_PUNCT_END.sub("", text)

    # ── 6. Remove isolated numbers (e.g. "مزرعة 12") ──
    text = _RE_DIGITS.sub("", text)

    # ── 7. Collapse spaces ──
    text = _RE_SPACES.sub(" ", text).strip()

    return text if text else normalize_arabic(safe_str(name))


def clean_rep_name(name) -> str:
    """
    Unify sales-rep name spelling: collapse spaces, Title Case for Latin
    names ("saif hassib" → "Saif Hassib"). Arabic names are only space-trimmed.
    """
    s = safe_str(name)
    s = _RE_SPACES.sub(" ", s).strip()
    if s and not contains_arabic(s):
        s = s.title()
    return s


def deduplicate_customer_names(df: pd.DataFrame, name_col: str = "Customer Name") -> pd.DataFrame:
    """Add 'Customer Name Cleaned' column used for grouping without overwriting original."""
    if name_col not in df.columns:
        return df
    df = df.copy()
    df["Customer Name Cleaned"] = df[name_col].apply(clean_customer_name)
    return df


def find_similar_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a summary of cleaned customer names.
    Flags names that have multiple spelling variants (potential duplicates).
    """
    if "Customer Name" not in df.columns:
        return pd.DataFrame()
    df_temp = deduplicate_customer_names(df)
    summary = (
        df_temp.groupby("Customer Name Cleaned")
        .agg(
            Visit_Count=("Customer Name", "count"),
            Original_Names=("Customer Name", lambda x: " | ".join(sorted(x.unique()[:6]))),
        )
        .reset_index()
        .rename(columns={
            "Customer Name Cleaned": "Cleaned Name",
            "Visit_Count":           "Visit Count",
            "Original_Names":        "Original Name Variants",
        })
        .sort_values("Visit Count", ascending=False)
        .reset_index(drop=True)
    )
    summary["Has Variants"] = summary["Original Name Variants"].str.contains(r"\|", regex=True)
    return summary


# ═══════════════════════════════════════════════════════════════════
# FILE LOADING
# ═══════════════════════════════════════════════════════════════════

def load_excel(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        df = df.rename(columns=COLUMN_ALIASES)

        # Auto-detect header row if columns are mostly unnamed
        unnamed_count = sum(1 for c in df.columns if "Unnamed" in str(c))
        if unnamed_count > len(df.columns) / 2:
            df = pd.read_excel(uploaded_file, engine="openpyxl", header=1)
            df = df.rename(columns=COLUMN_ALIASES)
        unnamed_count = sum(1 for c in df.columns if "Unnamed" in str(c))
        if unnamed_count > len(df.columns) / 2:
            df = pd.read_excel(uploaded_file, engine="openpyxl", header=2)
            df = df.rename(columns=COLUMN_ALIASES)

        df = df.dropna(how="all").reset_index(drop=True)
        return df, ""
    except Exception as e:
        return None, f"Failed to read file: {e}"


# ═══════════════════════════════════════════════════════════════════
# COLUMN VALIDATION
# ═══════════════════════════════════════════════════════════════════

def validate_columns(df: pd.DataFrame):
    present = list(df.columns)
    missing = [c for c in REQUIRED_COLUMNS if c not in present]
    return len(missing) == 0, missing, present


# ═══════════════════════════════════════════════════════════════════
# DATE PARSING
# ═══════════════════════════════════════════════════════════════════

def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    if "Visit Date" not in df.columns:
        return df
    df = df.copy()
    df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")
    return df


# ═══════════════════════════════════════════════════════════════════
# DATA CLEANING
# ═══════════════════════════════════════════════════════════════════

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full pipeline:
    1. Strip / fill text columns
    2. Parse flag columns
    3. Parse dates
    4. Sort by Visit Date
    5. Add Customer Name Cleaned column
    """
    df = df.copy()

    text_cols = [
        "Customer Name", "Customer Category", "Governorate",
        "District", "Visit Notes", "Sales Rep Name",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(safe_str)

    flag_cols = [
        "Current Customer", "Target Customer", "Potential Customer",
        "New Customer", "Not Interested Customer", "Former Customer",
        "Total Visit Flag", "Unique Customer Flag",
    ]
    for col in flag_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df = parse_dates(df)
    df = df.sort_values("Visit Date", ascending=True).reset_index(drop=True)

    # ── Sales Rep name unification (case / spacing duplicates) ──
    if "Sales Rep Name" in df.columns:
        df["Sales Rep Name"] = df["Sales Rep Name"].apply(clean_rep_name)

    # ── Customer Name Cleaning ──
    if "Customer Name" in df.columns:
        df["Customer Name Cleaned"] = df["Customer Name"].apply(clean_customer_name)

    return df


# ═══════════════════════════════════════════════════════════════════
# SUMMARY STATS
# ═══════════════════════════════════════════════════════════════════

def basic_stats(df: pd.DataFrame) -> dict:
    return {
        "total_records":    len(df),
        "unique_customers": df["Customer Name"].nunique() if "Customer Name" in df.columns else 0,
        "unique_reps":      df["Sales Rep Name"].nunique() if "Sales Rep Name" in df.columns else 0,
        "date_range_start": df["Visit Date"].min() if "Visit Date" in df.columns else None,
        "date_range_end":   df["Visit Date"].max() if "Visit Date" in df.columns else None,
        "governorates":     df["Governorate"].nunique() if "Governorate" in df.columns else 0,
    }


# ═══════════════════════════════════════════════════════════════════
# DATE / NUMBER HELPERS
# ═══════════════════════════════════════════════════════════════════

def days_since(last_date, reference_date=None):
    if reference_date is None:
        reference_date = pd.Timestamp(datetime.today().date())
    if pd.isnull(last_date):
        return None
    return (reference_date - pd.Timestamp(last_date)).days


def months_list(df: pd.DataFrame) -> list:
    if "Visit Date" not in df.columns:
        return []
    months = df["Visit Date"].dropna().dt.to_period("M").astype(str).unique().tolist()
    return sorted(months)


def fmt_number(n) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def fmt_pct(n, decimals=1) -> str:
    try:
        return f"{float(n):.{decimals}f}%"
    except Exception:
        return "—"
