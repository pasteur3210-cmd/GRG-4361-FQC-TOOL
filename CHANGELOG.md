## V1.0.2 — 2026-11-04
- Write all per-run FQC results and logs under `Records/` next to the packaged EXE.
- In source mode, write under `Records/` next to main.py.
- OPEN RECORDS and OPEN LAST RUN LOGS now point to the new path.
- Raise a clear GUI error if the EXE folder is not writable; do not silently redirect to Documents.
- Update Windows build artifact and EXE version to V1.0.2.
- Retain the V1.0.1 WAN parser fix and read-only device operations.

# Changelog

## V1.0.1 — 2026-11-04
- Fix incomplete WAN parsing of malformed HTML table, which silently skipped `nas0_1`. Select the more complete of normal row-based and sequential-cell fallback parsers.
- Add WAN regression tests: malformed intermediate row must be present; truly missing interface remains FAIL.
- Add OPEN RECORDS and OPEN LAST RUN LOGS buttons.
- Add HTTP read step audit markers in debug log and per-test results in execution log.
- Keep original read-only behavior, known bad GPON SN FAIL, and SN REVIEW pending approved range.

## V1.0.0
- Initial GRG-4361 FQC tool.
