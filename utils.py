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
    "Year",
    "Month",
    "Visit Date",
    "Customer Name",
    "Customer Category",
    "Governorate",
    "District",
    "Visit Notes",
    "Total Visit Flag",
    "Unique Customer Flag",
    "Sales Rep Name",
    "Current Customer",
    "Target Customer",
    "Potential Customer",
    "New Customer",
    "Not Interested Customer",
    "Former Customer",
]

# ─────────────────────────────────────────────
# COLUMN ALIASES (Arabic or alternate names)
# ─────────────────────────────────────────────

COLUMN_ALIASES = {
    "السنة": "Year",
    "الشهر": "Month",
    "تاريخ الزيارة": "Visit Date",
    "اسم العميل": "Customer Name",
    "فئة العميل": "Customer Category",
    "المحافظة": "Governorate",
    "المنطقة": "District",
    "ملاحظات الزيارة": "Visit Notes",
    "إجمالي الزيارات": "Total Visit Flag",
    "عميل فريد": "Unique Customer Flag",
    "اسم المندوب": "Sales Rep Name",
    "عميل حالي": "Current Customer",
    "عميل مستهدف": "Target Customer",
    "عميل محتمل": "Potential Customer",
    "عميل جديد": "New Customer",
    "غير مهتم": "Not Interested Customer",
    "عميل سابق": "Former Customer",
}

# ─────────────────────────────────────────────
# CUSTOMER STATUS LABELS
# ─────────────────────────────────────────────

STATUS_LABELS = {
    "current": "Current Customer",
    "potential": "Potential Customer",
    "target": "Target Customer",
    "new": "New Customer",
    "former": "Former Customer",
    "not_interested": "Not Interested",
    "unclassified": "Unclassified",
}

STATUS_COLORS = {
    "Current Customer":    "#70AD47",
    "Potential Customer":  "#2E75B6",
    "Target Customer":     "#FFC000",
    "New Customer":        "#1F4E79",
    "Former Customer":     "#A9A9A9",
    "Not Interested":      "#C00000",
    "Unclassified":        "#D9D9D9",
}

# ─────────────────────────────────────────────
# ARABIC TEXT HELPERS
# ─────────────────────────────────────────────

def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic text for keyword matching:
    - Strip whitespace
    - Unify Alef / Ya / Ta Marbuta variants
    - Remove Tashkeel (diacritics)
    - Remove Tatweel (kashida ـ)
    - Normalize spaces
    """
    if not isinstance(text, str):
        return ""

    text = text.strip()

    # ── Remove Tatweel (kashida) ──
    text = re.sub(r"ـ", "", text)

    # ── Remove Tashkeel / diacritics ──
    tashkeel = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]")
    text = tashkeel.sub("", text)

    # ── Unify Alef variants → ا ──
    text = re.sub(r"[إأآٱ]", "ا", text)

    # ── Unify Ta Marbuta → ه ──
    text = re.sub(r"ة", "ه", text)

    # ── Unify Ya variants → ي ──
    text = re.sub(r"[يى]", "ي", text)

    # ── Unify Waw variants ──
    text = re.sub(r"ؤ", "و", text)

    # ── Unify Hamza on Alef ──
    text = re.sub(r"ئ", "ي", text)

    # ── Normalize multiple spaces → single space ──
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ─────────────────────────────────────────────
# CUSTOMER NAME CLEANING
# ─────────────────────────────────────────────

# prefixes to strip from customer names
_NAME_PREFIXES = [
    "مزرعة", "مزارع", "مزرعه", "شركة", "شركه", "مؤسسة", "مؤسسه",
    "محل", "محلات", "مصنع", "مصانع", "مجمع", "مجموعة", "مجموعه",
    "م /", "م/", "أ /", "أ/", "ا/", "د /", "د/", "المهندس",
    "الحاج", "الحاجة", "الشيخ", "السيد", "الاستاذ", "الأستاذ",
    "مندوب", "صاحب",
]

# suffixes / noise words to strip
_NAME_SUFFIXES = [
    "للدواجن", "للتجارة", "للتجاره", "للانتاج", "للإنتاج",
    "للتسمين", "للبيض", "دواجن", "بروميل", "فروج",
    "- فرع", "فرع", "( تاجر )", "(تاجر)", "تاجر",
    "وكيل", "- وكيل",
]

# noise tokens to remove anywhere in name
_NOISE_TOKENS = [
    "ابو", "أبو", "بن", "بنت", "عبد", "عبده",
]


def clean_customer_name(name: str) -> str:
    """
    Clean and normalize a customer name for deduplication and matching.

    Steps:
    1. Apply normalize_arabic (Alef/Ya/diacritics/tatweel)
    2. Strip common prefixes (مزرعة / شركة / الحاج ...)
    3. Strip common suffixes (للدواجن / دواجن ...)
    4. Remove extra punctuation and special characters
    5. Collapse multiple spaces
    6. Title-case equivalent for Arabic (preserve original casing)

    Returns cleaned name. Original is preserved in the DataFrame;
    the cleaned version is used only for grouping/deduplication.
    """
    if not isinstance(name, str) or not name.strip():
        return ""

    cleaned = safe_str(name)

    # ── Step 1: Arabic normalization ──
    cleaned = normalize_arabic(cleaned)

    # ── Step 2: Remove leading prefixes ──
    changed = True
    while changed:
        changed = False
        for prefix in _NAME_PREFIXES:
            prefix_norm = normalize_arabic(prefix)
            if cleaned.startswith(prefix_norm + " ") or cleaned == prefix_norm:
                cleaned = cleaned[len(prefix_norm):].strip()
                changed = True
            # Also handle prefix without space (e.g. "م/أحمد")
            if cleaned.startswith(prefix_norm):
                cleaned = cleaned[len(prefix_norm):].strip()
                changed = True

    # ── Step 3: Remove trailing suffixes ──
    for suffix in _NAME_SUFFIXES:
        suffix_norm = normalize_arabic(suffix)
        if cleaned.endswith(" " + suffix_norm) or cleaned == suffix_norm:
            cleaned = cleaned[: -len(suffix_norm)].strip()
        if cleaned.endswith(suffix_norm):
            cleaned = cleaned[: -len(suffix_norm)].strip()

    # ── Step 4: Remove punctuation noise ──
    # Remove brackets, slashes, dashes at start/end
    cleaned = re.sub(r"^[\-–/\\()\[\]،,\.]+", "", cleaned)
    cleaned = re.sub(r"[\-–/\\()\[\]،,\.]+$", "", cleaned)

    # ── Step 5: Remove numbers-only segments ──
    cleaned = re.sub(r"\b\d{1,3}\b", "", cleaned)

    # ── Step 6: Collapse spaces ──
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def deduplicate_customer_names(df: pd.DataFrame, name_col: str = "Customer Name") -> pd.DataFrame:
    """
    Add a 'Customer Name Cleaned' column to the DataFrame.
    Used for grouping/analytics without overwriting the original name.
    """
    if name_col not in df.columns:
        return df
    df = df.copy()
    df["Customer Name Cleaned"] = df[name_col].apply(clean_customer_name)
    return df


def find_similar_customers(df: pd.DataFrame, threshold: int = 85) -> pd.DataFrame:
    """
    Find customer names that are likely duplicates based on cleaned names.
    Returns a DataFrame of (Original Name, Cleaned Name, Match Count).
    """
    if "Customer Name" not in df.columns:
        return pd.DataFrame()

    df_temp = deduplicate_customer_names(df)
    cleaned_counts = (
        df_temp.groupby("Customer Name Cleaned")
        .agg(
            Visit_Count=("Customer Name", "count"),
            Original_Names=("Customer Name", lambda x: " | ".join(x.unique()[:5])),
        )
        .reset_index()
        .rename(columns={
            "Customer Name Cleaned": "Cleaned Name",
            "Visit_Count":          "Visit Count",
            "Original_Names":       "Original Name Variants",
        })
        .sort_values("Visit Count", ascending=False)
    )

    # Flag names with multiple variants (potential duplicates)
    cleaned_counts["Has Variants"] = cleaned_counts["Original Name Variants"].str.contains(r"\|")

    return cleaned_counts


# ─────────────────────────────────────────────
# FILE LOADING
# ─────────────────────────────────────────────

def load_excel(uploaded_file) -> tuple[pd.DataFrame | None, str]:
    """
    Load an uploaded Excel file into a DataFrame.
    Returns (df, error_message). error_message is empty string on success.
    """
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        # Rename columns using alias map
        df = df.rename(columns=COLUMN_ALIASES)
        return df, ""
    except Exception as e:
        return None, f"Failed to read file: {e}"


# ─────────────────────────────────────────────
# COLUMN VALIDATION
# ─────────────────────────────────────────────

def validate_columns(df: pd.DataFrame) -> tuple[bool, list[str], list[str]]:
    """
    Validate that required columns are present.
    Returns (is_valid, missing_cols, present_cols).
    """
    present = list(df.columns)
    missing = [c for c in REQUIRED_COLUMNS if c not in present]
    is_valid = len(missing) == 0
    return is_valid, missing, present


# ─────────────────────────────────────────────
# DATE PARSING
# ─────────────────────────────────────────────

def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and clean the Visit Date column."""
    if "Visit Date" not in df.columns:
        return df
    df = df.copy()
    df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")
    return df


# ─────────────────────────────────────────────
# DATA CLEANING
# ─────────────────────────────────────────────

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply baseline cleaning:
    - Strip string columns
    - Fill NaN in text columns with empty string
    - Parse dates
    - Sort by Visit Date ascending
    - Add Customer Name Cleaned column
    """
    df = df.copy()

    text_cols = [
        "Customer Name", "Customer Category", "Governorate",
        "District", "Visit Notes", "Sales Rep Name",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(safe_str)

    # ── Customer Name Cleaning ──
    if "Customer Name" in df.columns:
        df["Customer Name Cleaned"] = df["Customer Name"].apply(clean_customer_name)

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
    return df


# ─────────────────────────────────────────────
# SUMMARY STATS
# ─────────────────────────────────────────────

def basic_stats(df: pd.DataFrame) -> dict:
    """Return a dict of basic dataset statistics."""
    stats = {
        "total_records": len(df),
        "unique_customers": df["Customer Name"].nunique() if "Customer Name" in df.columns else 0,
        "unique_reps": df["Sales Rep Name"].nunique() if "Sales Rep Name" in df.columns else 0,
        "date_range_start": df["Visit Date"].min() if "Visit Date" in df.columns else None,
        "date_range_end": df["Visit Date"].max() if "Visit Date" in df.columns else None,
        "governorates": df["Governorate"].nunique() if "Governorate" in df.columns else 0,
    }
    return stats


# ─────────────────────────────────────────────
# DATE HELPERS
# ─────────────────────────────────────────────

def days_since(last_date, reference_date=None) -> int | None:
    """Return number of days between last_date and reference_date (today if None)."""
    if reference_date is None:
        reference_date = pd.Timestamp(datetime.today().date())
    if pd.isnull(last_date):
        return None
    delta = reference_date - pd.Timestamp(last_date)
    return delta.days


def months_list(df: pd.DataFrame) -> list[str]:
    """Return sorted list of 'YYYY-MM' strings from Visit Date column."""
    if "Visit Date" not in df.columns:
        return []
    dates = df["Visit Date"].dropna()
    months = dates.dt.to_period("M").astype(str).unique().tolist()
    return sorted(months)


# ─────────────────────────────────────────────
# NUMBER FORMATTING
# ─────────────────────────────────────────────

def fmt_number(n) -> str:
    """Format an integer with comma separators."""
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def fmt_pct(n, decimals=1) -> str:
    """Format a float as a percentage string."""
    try:
        return f"{float(n):.{decimals}f}%"
    except Exception:
        return "—"


