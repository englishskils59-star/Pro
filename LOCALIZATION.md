# Arabic / English interface

Arabic remains the default. Use **العربية | English** below the sidebar logo to switch. The browser stores the preference in localStorage (`wdi.interface.language`); no shared configuration or business records are written. The document `lang` and `dir` attributes follow the selection.

Requires Streamlit 1.58 or later (the version already installed for this project). Run the application using the existing Streamlit command.

## Localization boundaries

- `localization.py` centralizes language state, the UI facade, display-only chart/table copies, and translated message templates.
- `translations.en.json` maps exact original Arabic text to English. Unknown strings return the original Arabic. Add translations here; keep Arabic navigation values, status identifiers, data columns and comparison keys unchanged.
- The small component in `static/language/` provides the switcher and browser preference. It does not submit forms or access business data.
- Dynamic UI templates translate their literal parts separately from inserted names, notes, paths and file names. Free-form Arabic text remains readable using the original font and bidirectional text isolation.
- Widget, tab and expander keys are independent of translated labels. Changing language continues the same Streamlit session and preserves current page, filters and pending form edits.
- Human-readable reports localize headings, generated enum labels and worksheet direction. Raw classification and manual-override import/export schemas retain their integration column names and internal status values. Existing English labels in the original Arabic experience remain as originally designed.
- Cached human-readable reports regenerate their presentation from their existing source data after a language change, without changing selected report data.

## Verification

Run `python -m unittest discover -s tests -v` for dictionary fallback, record/schema isolation, chart copy and report checks.

Run `python tests/browser_localization.py` against the existing service at `http://localhost:8501` when Playwright and Microsoft Edge are available. This read-only test checks language direction, page/search/status preservation, an unsubmitted rule field, refresh persistence, mobile LTR layout, six key-screen PNGs and business-file hashes. It never submits a rule or edits business records. Each run writes to a new UTC-timestamped subfolder of `screenshots`.
