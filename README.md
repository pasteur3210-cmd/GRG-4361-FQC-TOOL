# GRG-4361 FQC Test Tool V1.0.4

Windows 11 English standalone FQC tool built by GitHub Actions (Python 3.11). Uses the proven V1.0.3 Router HTTP client and is **read-only**.

## Production sequence
1. Set Router IP, username, password, approved FW and operator.
2. Scan **Chassis Label SN (20 characters)**, **MAC (12 hex)**, **GPON SN (CMTD + 8 hex)**. Barcode scanner should send Enter after scanning; focus advances automatically.
3. Click **START READ-ONLY CHECK**.
4. **LED STEP 1** (before fiber): verify Power green ON, Phone OFF, LAN LED blue ON if the qualified LAN link is attached, PON red blinking. Select PASS or FAIL. PASS receives keyboard focus but is NEVER automatically accepted. FAIL records a failed attempt and skips HTTP checks.
5. **LED STEP 2**: lift handset; verify Phone green blinking; connect fiber to an OLT; when registered verify PON green solid. Select PASS or FAIL. FAIL records failed attempt and skips HTTP checks.
6. HTTP login, GET `status.asp`, GET `gpon.asp`, then poll `status_pon.asp` (2-second interval, max 60 seconds) until ONU State O5. Optical measurements are valid only after O5. If O5 is not achieved, final result FAIL and no Tx PASS is possible.
7. Compare scanned MAC and GPON SN to Router values; check GPON SN = CMTD + MAC final eight hex digits; check model, FW and WAN profiles.
8. **Tx optical power specification in code: 6.8–7.2 dBm (inclusive)**. Missing/No signal fails; response with an unexpected unit such as V is ERROR. This is a provisional interpretation of the user's '6.8~7.2V' instruction and MUST be approved against equipment output before production release. Other PON values are informational.
9. Save per-run Excel, result.json, execution/test/debug logs; append to FQC Master Excel. Same SN retests are retained. SN shipment-range checking remains REVIEW until a verified range is supplied, so even valid readings do not result in overall PASS.

## Operator UI
Single START button; other functions moved to **Maintenance** menu: Open Records, Open Last Run Logs, Open Master, Sync Master.

## Log location
`<EXE folder>/Records/<run-id>/` contains the individual `FQC_Result.xlsx`, `result.json`, `execution.log`, `test.log`, `debug.log`. Master located at `<EXE folder>/Records/GRG-4361_FQC_Master_Record.xlsx`.

## GitHub build
Upload clean ZIP contents to repository root, preserving `.github/workflows/build-windows.yml`. Go to Actions → GRG-4361 FQC Windows Build → Run workflow. Download artifact `GRG-4361-FQC-V1.0.4`.

## Release restrictions
- No settings POST, reset, upgrade, or vendor-specific OLT control. Fiber registration depends on external OLT connectivity.
- Optical Tx thresholds, LED expectations, FW Golden, WAN Golden, and SN production range require formal factory sign-off before full release.
- `DUT SN` in Router web status is not known; label SN cannot yet be compared to a device-read SN.
- A failed HTTP connection may produce execution/debug logs without a complete FQC Master row; engineering ERROR attempts are kept in per-run logs.
- Validate on real Windows 11 English PC and DUT before factory release. Do not expose login credentials or tokens in logs/screenshots.
