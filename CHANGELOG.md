# CHANGELOG

## V1.0.3 — Cumulative factory FQC Master Record
- Added cumulative `Records/GRG-4361_FQC_Master_Record.xlsx`, with `All Tests` and `Summary` tabs.
- Preserved existing per-test Excel, JSON, execution/test/debug logs.
- Added operator input, per-run unique ID, test timestamp, per-SN Retest No., Record Path, WAN and PON columns.
- Added idempotent Master sync, interprocess write lock, atomic XLSX replacement, and recovery from temporarily locked workbook via SYNC MASTER.
- Added OPEN MASTER and SYNC MASTER buttons. On failure Master stays pending; no test data are overwritten.
- Preserved V1.0.2 WAN nas0_1 malformed-HTML fix and EXE-local Records path.
- Updated GitHub artifact and EXE version to V1.0.3.

## V1.0.2
- Records moved next to EXE and added open-folder controls.

## V1.0.1
- Corrected middle WAN entry parser fallback and logging.
