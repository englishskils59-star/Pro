"""Explicit, versioned human labels for offline evaluation; never auto-trains.

No database is created on import. Call record_correction with a separate path
only after a human has actually approved a label. Historical overrides without
reviewer/time provenance are NOT automatically imported as training labels.
"""
from pathlib import Path
from datetime import datetime,timezone
import sqlite3
from contextlib import closing
import hashlib
from classification_context import normalize_note, DEFINITIONS_VERSION, text_value
from classification_engine import STATUS_DISPLAY


def record_correction(path, *, record_id, text, approved_status, approved_by,
                      source, definitions_version=DEFINITIONS_VERSION):
    fields=[record_id,text,approved_status,approved_by,source,definitions_version]
    if not all(text_value(v) for v in fields):
        raise ValueError('Record, text, human reviewer, source and definitions version are required')
    if approved_status not in STATUS_DISPLAY.values():
        raise ValueError('Unknown approved status')
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('PRAGMA busy_timeout=5000')
        db.execute('''CREATE TABLE IF NOT EXISTS corrections (
          revision INTEGER PRIMARY KEY AUTOINCREMENT,
          record_id TEXT NOT NULL, original_text TEXT NOT NULL,
          normalized_hash TEXT NOT NULL, approved_status TEXT NOT NULL,
          approved_by TEXT NOT NULL, corrected_at TEXT NOT NULL,
          definitions_version TEXT NOT NULL, source TEXT NOT NULL)''')
        cur=db.execute('INSERT INTO corrections(record_id,original_text,normalized_hash,approved_status,approved_by,corrected_at,definitions_version,source) VALUES (?,?,?,?,?,?,?,?)',
          (str(record_id),str(text),hashlib.sha256(normalize_note(text).encode()).hexdigest(),approved_status,
           str(approved_by),datetime.now(timezone.utc).isoformat(),str(definitions_version),str(source)))
        return cur.lastrowid


def approved_labels(path):
    """Read only the newest explicit revision per record; preserve all history."""
    path=Path(path)
    if not path.exists(): return []
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute('SELECT * FROM corrections WHERE revision IN (SELECT MAX(revision) FROM corrections GROUP BY record_id) ORDER BY revision')]


def evaluation_groups(rows, similarity=0.9):
    """Conservative near-duplicate connected groups, independent of labels.

    Intended for a small curated corpus. A caller must ALSO hold out customers
    and later dates. Group assignment alone is not an evaluation or an accuracy.
    """
    from difflib import SequenceMatcher
    notes=[normalize_note(r['original_text']) for r in rows]
    parents=list(range(len(notes)))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,a in enumerate(notes):
        for j in range(i):
            if a==notes[j] or SequenceMatcher(None,a,notes[j],autojunk=False).ratio()>=similarity:
                parents[find(i)]=find(j)
    return [find(i) for i in range(len(notes))]
