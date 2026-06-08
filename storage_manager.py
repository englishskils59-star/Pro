# storage_manager.py
# WDI Visit Analytics Engine
# Persistent storage manager — saves/loads data from shared folder
# Supports multi-user access via network shared drive

import os
import json
import shutil
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# CONFIG FILE — stores the shared folder path
# ═══════════════════════════════════════════════════════════════════

CONFIG_FILE = Path(__file__).parent / "wdi_config.json"
DEFAULT_DATA_DIR = Path(__file__).parent / "data"


def load_config() -> dict:
    """Load app configuration from local config file."""
    default = {
        "data_dir": str(DEFAULT_DATA_DIR),
        "app_version": "1.0",
        "last_updated": "",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # Merge with defaults for any missing keys
                for k, v in default.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception:
            return default
    return default


def save_config(config: dict):
    """Save configuration to local config file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        return False


def get_data_dir() -> Path:
    """Get the configured data directory path."""
    cfg = load_config()
    return Path(cfg.get("data_dir", str(DEFAULT_DATA_DIR)))


def set_data_dir(path: str) -> tuple[bool, str]:
    """
    Set the shared data directory path.
    Creates the directory if it doesn't exist.
    Returns (success, message).
    """
    try:
        p = Path(path.strip())
        p.mkdir(parents=True, exist_ok=True)

        # Test write access
        test_file = p / ".wdi_test"
        test_file.write_text("test")
        test_file.unlink()

        cfg = load_config()
        cfg["data_dir"] = str(p)
        save_config(cfg)
        return True, f"✅ تم تعيين مسار البيانات: {p}"
    except PermissionError:
        return False, f"❌ لا توجد صلاحية كتابة في: {path}"
    except Exception as e:
        return False, f"❌ خطأ: {e}"


# ═══════════════════════════════════════════════════════════════════
# FILE PATHS
# ═══════════════════════════════════════════════════════════════════

def _paths() -> dict:
    """Return all data file paths based on current data_dir."""
    d = get_data_dir()
    return {
        "metadata":    d / "metadata.json",
        "classified":  d / "classified_data.parquet",
        "journey":     d / "journey_data.parquet",
        "rep_kpi":     d / "rep_kpi_data.parquet",
        "overrides":   d / "overrides.parquet",
        "raw_backup":  d / "last_upload.xlsx",
    }


# ═══════════════════════════════════════════════════════════════════
# METADATA
# ═══════════════════════════════════════════════════════════════════

def _load_metadata() -> dict:
    paths = _paths()
    if paths["metadata"].exists():
        try:
            with open(paths["metadata"], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_metadata(meta: dict):
    paths = _paths()
    paths["metadata"].parent.mkdir(parents=True, exist_ok=True)
    meta["last_saved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════════

def save_session(
    classified_df: pd.DataFrame,
    journey_df: pd.DataFrame,
    rep_kpi_df: pd.DataFrame,
    file_name: str = "",
    uploaded_file=None,
) -> tuple[bool, str]:
    """
    Save current session data to the shared data directory.
    Returns (success, message).
    """
    try:
        paths = _paths()
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)

        # ── Save classified data ──
        _df_to_parquet(classified_df, paths["classified"])

        # ── Save journey data (drop internal columns) ──
        journey_save = journey_df.copy()
        if "_journey" in journey_save.columns:
            journey_save = journey_save.drop(columns=["_journey"])
        _df_to_parquet(journey_save, paths["journey"])

        # ── Save rep KPI ──
        if rep_kpi_df is not None and not rep_kpi_df.empty:
            _df_to_parquet(rep_kpi_df, paths["rep_kpi"])

        # ── Save raw file backup ──
        if uploaded_file is not None:
            try:
                uploaded_file.seek(0)
                with open(paths["raw_backup"], "wb") as f:
                    f.write(uploaded_file.read())
            except Exception:
                pass

        # ── Save metadata ──
        meta = {
            "file_name":       file_name,
            "total_records":   len(classified_df),
            "unique_customers":classified_df["Customer Name"].nunique() if "Customer Name" in classified_df.columns else 0,
            "unique_reps":     classified_df["Sales Rep Name"].nunique() if "Sales Rep Name" in classified_df.columns else 0,
            "date_range_start":str(classified_df["Visit Date"].min())[:10] if "Visit Date" in classified_df.columns else "",
            "date_range_end":  str(classified_df["Visit Date"].max())[:10] if "Visit Date" in classified_df.columns else "",
            "override_count":  0,
        }
        _save_metadata(meta)

        return True, "✅ تم حفظ البيانات بنجاح"
    except Exception as e:
        return False, f"❌ خطأ في الحفظ: {e}"


# ═══════════════════════════════════════════════════════════════════
# LOAD
# ═══════════════════════════════════════════════════════════════════

def load_session() -> tuple[bool, dict]:
    """
    Load saved session from shared data directory.
    Returns (success, data_dict).
    data_dict keys: classified_df, journey_df, rep_kpi_df, metadata
    """
    try:
        paths = _paths()

        if not paths["classified"].exists():
            return False, {}

        classified_df = _parquet_to_df(paths["classified"])
        journey_df    = _parquet_to_df(paths["journey"]) if paths["journey"].exists() else pd.DataFrame()
        rep_kpi_df    = _parquet_to_df(paths["rep_kpi"]) if paths["rep_kpi"].exists() else pd.DataFrame()
        metadata      = _load_metadata()

        # Apply any saved overrides
        classified_df, override_count = _apply_saved_overrides(classified_df)

        return True, {
            "classified_df": classified_df,
            "journey_df":    journey_df,
            "rep_kpi_df":    rep_kpi_df,
            "metadata":      metadata,
            "override_count":override_count,
        }
    except Exception as e:
        return False, {"error": str(e)}


def has_saved_data() -> bool:
    """Check if saved data exists in the data directory."""
    return _paths()["classified"].exists()


def get_saved_metadata() -> dict:
    """Get metadata of saved session without loading full data."""
    return _load_metadata()


# ═══════════════════════════════════════════════════════════════════
# OVERRIDE SYSTEM
# ═══════════════════════════════════════════════════════════════════

VALID_STATUSES = [
    "Current Customer",
    "Potential Customer",
    "Target Customer",
    "New Customer",
    "Former Customer",
    "Not Interested",
]


def export_unclassified(classified_df: pd.DataFrame) -> bytes:
    """
    Export Unclassified rows as Excel for manual classification.
    Includes Row Number as the key for matching on re-import.
    """
    import io
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    # Get unclassified rows with their original row numbers
    mask = classified_df["Display Status"] == "Unclassified"
    unclass = classified_df[mask].copy()
    unclass.insert(0, "Row Number", unclass.index)

    # Select display columns
    show_cols = ["Row Number", "Visit Date", "Customer Name", "Sales Rep Name",
                 "Governorate", "District", "Visit Notes", "Display Status"]
    show_cols = [c for c in show_cols if c in unclass.columns]
    unclass = unclass[show_cols].copy()

    # Add empty Manual Status column
    unclass["Manual Status"] = ""

    # Format dates
    if "Visit Date" in unclass.columns:
        unclass["Visit Date"] = pd.to_datetime(
            unclass["Visit Date"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    # Build Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Unclassified Visits"
    ws.sheet_view.rightToLeft = True

    # Header style
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
    manual_fill = PatternFill("solid", fgColor="E2EFDA")  # Green tint for manual column
    border = Border(
        left=Side(border_style="thin", color="B8CCE4"),
        right=Side(border_style="thin", color="B8CCE4"),
        top=Side(border_style="thin", color="B8CCE4"),
        bottom=Side(border_style="thin", color="B8CCE4"),
    )

    # Write header
    for col_idx, col_name in enumerate(unclass.columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font   = header_font
        cell.fill   = manual_fill if col_name == "Manual Status" else header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Write data
    for row_idx, row in enumerate(unclass.itertuples(index=False), start=2):
        fill = PatternFill("solid", fgColor="EBF3FB") if row_idx % 2 == 0 else PatternFill()
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            col_name = unclass.columns[col_idx - 1]
            if col_name == "Manual Status":
                cell.fill = PatternFill("solid", fgColor="E2EFDA")
            else:
                cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)

    # Add dropdown validation note
    ws.cell(row=1, column=len(unclass.columns), value="Manual Status").comment = None

    # Auto width
    from openpyxl.utils import get_column_letter
    for col in ws.columns:
        max_len = max((len(str(c.value)) if c.value else 0 for c in col), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(50, max(12, max_len + 4))

    # Notes column wider
    ws.column_dimensions["G"].width = 60
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "B2"

    # Add valid statuses note in a separate sheet
    ws2 = wb.create_sheet("القيم المسموح بها")
    ws2.cell(row=1, column=1, value="القيم المسموح بها في عمود Manual Status")
    ws2.cell(row=1, column=1).font = Font(bold=True, color="1F4E79")
    for i, status in enumerate(VALID_STATUSES, start=2):
        ws2.cell(row=i, column=1, value=status)
    ws2.column_dimensions["A"].width = 30

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def import_overrides(
    override_file,
    classified_df: pd.DataFrame,
) -> tuple[pd.DataFrame, int, list[str]]:
    """
    Import manual classifications from uploaded override file.

    Returns:
        (updated_classified_df, count_changed, errors_list)
    """
    errors = []

    try:
        override_df = pd.read_excel(override_file, engine="openpyxl")
    except Exception as e:
        return classified_df, 0, [f"❌ لا يمكن قراءة الملف: {e}"]

    # Validate required columns
    if "Row Number" not in override_df.columns:
        return classified_df, 0, ["❌ عمود 'Row Number' غير موجود في الملف"]
    if "Manual Status" not in override_df.columns:
        return classified_df, 0, ["❌ عمود 'Manual Status' غير موجود في الملف"]

    # Filter rows with actual manual status
    override_df = override_df[
        override_df["Manual Status"].notna() &
        (override_df["Manual Status"].astype(str).str.strip() != "")
    ].copy()

    if override_df.empty:
        return classified_df, 0, ["⚠️ لا توجد تصنيفات يدوية في الملف — عمود Manual Status فارغ"]

    # Validate status values
    invalid_rows = []
    for _, row in override_df.iterrows():
        status = str(row["Manual Status"]).strip()
        if status not in VALID_STATUSES:
            invalid_rows.append(f"صف {row['Row Number']}: قيمة غير معروفة '{status}'")

    if invalid_rows:
        errors.extend(invalid_rows[:10])  # Show max 10 errors
        # Remove invalid rows
        override_df = override_df[
            override_df["Manual Status"].astype(str).str.strip().isin(VALID_STATUSES)
        ]

    # Apply overrides to classified_df
    updated_df = classified_df.copy()
    count_changed = 0

    for _, row in override_df.iterrows():
        row_num = int(row["Row Number"])
        new_status = str(row["Manual Status"]).strip()

        if row_num not in updated_df.index:
            errors.append(f"⚠️ رقم الصف {row_num} غير موجود في البيانات")
            continue

        # Apply the override
        updated_df.at[row_num, "Display Status"]   = new_status
        updated_df.at[row_num, "Suggested Status"]  = _display_to_internal(new_status)
        updated_df.at[row_num, "Override Source"]   = "Manual"
        updated_df.at[row_num, "Confidence Score"]  = 100.0
        count_changed += 1

    # Save overrides to disk for persistence
    if count_changed > 0:
        _save_overrides(override_df[["Row Number", "Manual Status"]])

    return updated_df, count_changed, errors


def _display_to_internal(display: str) -> str:
    """Convert display status to internal key."""
    mapping = {
        "Current Customer":   "current",
        "Potential Customer": "potential",
        "Target Customer":    "target",
        "New Customer":       "new",
        "Former Customer":    "former",
        "Not Interested":     "not_interested",
        "Unclassified":       "unclassified",
    }
    return mapping.get(display, "unclassified")


def _save_overrides(override_df: pd.DataFrame):
    """Save overrides to parquet for persistence."""
    paths = _paths()
    paths["overrides"].parent.mkdir(parents=True, exist_ok=True)

    existing = pd.DataFrame()
    if paths["overrides"].exists():
        try:
            existing = _parquet_to_df(paths["overrides"])
        except Exception:
            existing = pd.DataFrame()

    if not existing.empty and "Row Number" in existing.columns:
        # Merge: new overrides overwrite existing ones for same row
        combined = pd.concat([existing, override_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Row Number"], keep="last")
    else:
        combined = override_df.copy()

    _df_to_parquet(combined, paths["overrides"])

    # Update metadata
    meta = _load_metadata()
    meta["override_count"] = len(combined)
    _save_metadata(meta)


def _apply_saved_overrides(classified_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Apply any saved overrides to classified_df on load."""
    paths = _paths()

    if not paths["overrides"].exists():
        return classified_df, 0

    try:
        overrides = _parquet_to_df(paths["overrides"])
        if overrides.empty:
            return classified_df, 0

        updated = classified_df.copy()
        count = 0

        for _, row in overrides.iterrows():
            row_num    = int(row["Row Number"])
            new_status = str(row["Manual Status"]).strip()

            if row_num not in updated.index:
                continue
            if new_status not in VALID_STATUSES:
                continue

            updated.at[row_num, "Display Status"]  = new_status
            updated.at[row_num, "Suggested Status"] = _display_to_internal(new_status)
            updated.at[row_num, "Override Source"]  = "Manual"
            updated.at[row_num, "Confidence Score"] = 100.0
            count += 1

        return updated, count
    except Exception:
        return classified_df, 0


def clear_overrides() -> tuple[bool, str]:
    """Delete all saved overrides."""
    paths = _paths()
    try:
        if paths["overrides"].exists():
            paths["overrides"].unlink()
        meta = _load_metadata()
        meta["override_count"] = 0
        _save_metadata(meta)
        return True, "✅ تم حذف كل التصنيفات اليدوية"
    except Exception as e:
        return False, f"❌ خطأ: {e}"


def clear_all_data() -> tuple[bool, str]:
    """Delete all saved data (reset)."""
    try:
        data_dir = get_data_dir()
        for f in data_dir.glob("*.parquet"):
            f.unlink()
        for f in data_dir.glob("*.json"):
            f.unlink()
        for f in data_dir.glob("*.xlsx"):
            f.unlink()
        return True, "✅ تم حذف كل البيانات المحفوظة"
    except Exception as e:
        return False, f"❌ خطأ: {e}"


# ═══════════════════════════════════════════════════════════════════
# PARQUET HELPERS (fast binary format, better than CSV/Excel)
# ═══════════════════════════════════════════════════════════════════

def _df_to_parquet(df: pd.DataFrame, path: Path):
    """Save DataFrame as parquet with date handling."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df_save = df.copy()
    # Convert datetime columns to string to avoid timezone issues
    for col in df_save.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        df_save[col] = df_save[col].astype(str)
    df_save.to_parquet(str(path), index=True, engine="pyarrow" if _has_pyarrow() else "fastparquet")


def _parquet_to_df(path: Path) -> pd.DataFrame:
    """Load DataFrame from parquet."""
    df = pd.read_parquet(str(path), engine="pyarrow" if _has_pyarrow() else "fastparquet")
    # Re-parse Visit Date if it was stored as string
    if "Visit Date" in df.columns and df["Visit Date"].dtype == object:
        df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")
    return df


def _has_pyarrow() -> bool:
    try:
        import pyarrow
        return True
    except ImportError:
        return False


# ═══════════════════════════════════════════════════════════════════
# STORAGE STATUS
# ═══════════════════════════════════════════════════════════════════

def storage_status() -> dict:
    """Return storage health info for display in Settings page."""
    data_dir = get_data_dir()
    paths    = _paths()
    meta     = _load_metadata()

    files_exist = {k: v.exists() for k, v in paths.items()}
    total_size  = sum(
        v.stat().st_size for v in paths.values() if v.exists()
    )

    return {
        "data_dir":       str(data_dir),
        "dir_exists":     data_dir.exists(),
        "dir_writable":   _test_write(data_dir),
        "has_data":       files_exist.get("classified", False),
        "has_overrides":  files_exist.get("overrides", False),
        "total_size_kb":  round(total_size / 1024, 1),
        "metadata":       meta,
        "files":          files_exist,
    }


def _test_write(path: Path) -> bool:
    try:
        test = path / ".write_test"
        test.write_text("x")
        test.unlink()
        return True
    except Exception:
        return False
