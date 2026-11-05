# GRG-4361 FQC Test Tool V1.0.3

Windows 11 English GUI for read-only GRG-4361 factory FQC. Compiles to a standalone EXE through GitHub Actions (no Python needed on the test PC).

## Tests
Logs into Router via the existing V1.0.2 HTTP Session client and reads `/status.asp`, `/gpon.asp`, `/status_pon.asp`. Checks model, operator-approved FW, MAC format, GPON SN = `CMTD` + MAC last 8 digits, and the three GRG-4361 WAN entries. PON optical and ONU readings are recorded as INFO. The DUT SN is scanner/manual input, and its shipment-range check stays REVIEW until an approved range exists.

## V1.0.3 cumulative FQC records
Every test first saves independent records in `<EXE folder>/Records/<unique run ID>/`:
`FQC_Result.xlsx`, `result.json`, `execution.log`, `test.log`, `debug.log`.

The same `Records` directory contains `GRG-4361_FQC_Master_Record.xlsx`:
- **All Tests:** one row per test attempt, all key identity, WAN, PON, failure and review fields, Test ID, operator, timestamp, Retest No., individual Record Path.
- **Summary:** Excel formulas count attempts and PASS / FAIL / REVIEW / ERROR results. Numbers calculate when opened in Excel.
- Repeated DUT SN does **not** overwrite previous rows; Retest No. increases for repeated SN.
- Each run is identified by its unique per-run folder name; syncing again does not duplicate results.
- The program tries to append after each completed test and provides **SYNC MASTER** to import pending independent records.
- If the Master Excel is open/locked, standalone results survive unchanged and GUI shows `MASTER PENDING`. Close the Master workbook and click `SYNC MASTER` to recover.
- To reduce chance of corruption, the Master is written to a temporary workbook before atomic replacement. An interprocess file lock limits simultaneous writers on one workstation.
- A test ending in a technical error does not create a normal `result.json`; it is not counted as completed FQC inspection in Master. See execution/debug logs.
- `OPEN MASTER`, `OPEN RECORDS`, `OPEN LAST RUN LOGS` buttons are available.

## Build
Upload *contents* of Clean GitHub Upload to repository root, including `.github/workflows/build-windows.yml`.
Actions > GRG-4361 FQC Windows Build > Run workflow, then download artifact `GRG-4361-FQC-V1.0.3`.

## Important production limits
- Read-only. No setting changes, reset, firmware upgrade or OLT commands.
- WAN Golden is based on currently reviewed GRG-4361 screenshots; must be approved for the production release.
- An entered firmware value is an operator-supplied candidate, not verified against a BOM by software.
- SN remains REVIEW without an approved shipment range and should **not** authorize product release.
- Unconnected PON `O1` and `No signal` are INFO, not functional PASS.
- Test the built EXE on the target US Windows 11 English workstation and real GRG-4361 before factory deployment.
- Protect `Records` as potentially containing production identifiers. Do not share unredacted logs or result files publicly.
- EXE folder must be writable; do not put it under Program Files.

## Logs
Records stay next to EXE. `execution.log`, `test.log` and `debug.log` are generated for each successful test attempt and include Master sync status. No plaintext login passwords or HTTP authentication tokens are intentionally included.
