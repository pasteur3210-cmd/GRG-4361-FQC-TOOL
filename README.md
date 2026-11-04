# GRG-4361 FQC Test Tool V1.0

English Windows GUI, read-only inspection of a GRG-4361 router using the same HTTP login and Session implementation introduced in Router Label Verification Tool V1.0.12.

## Intended environment
- Build: GitHub Actions / Python 3.11 / Windows runner
- Run: Windows 11 English (US), no Python installation required
- Target: HTTP router at 192.168.1.1, operator-provided credentials

## Inspection actions
1. Login with existing `router_oqc.client.RouterClient` (CSRF and encoded password).
2. Read `status.asp` for model, firmware, MAC and WAN interface table.
3. Read `gpon.asp` for GPON SN.
4. Read `status_pon.asp` for PON optical values and ONU State.
5. Compare model, MAC format, GPON SN = `CMTD` + MAC last 8 hexadecimal digits, and WAN entries to the project-approved candidate profile.
6. Save Excel, JSON, `execution.log`, `test.log`, `debug.log` for each run in `Documents/GRG-4361_FQC_Records/<timestamp>`.

## Limitations and interpretation
- No configuration writes, restore, reboot, upgrade or OLT management are implemented.
- Firmware Golden is operator-entered: if blank the result remains REVIEW.
- SN has no verified web source or approved shipment-range list yet: SN always remains REVIEW; do not treat it as PASS.
- WAN expected values are initial candidate rules from the screenshots and need production Golden approval.
- PON optical readings and ONU State are INFO only until live PON test requirements are approved.
- LAN speed and VoIP are deferred from the active first-phase checks.
- Do not use the output as a factory release authorization while any REVIEW remains.
- The EXE and real HTTP login must be validated on an actual GRG-4361 and Windows 11 US workstation. Unit tests alone do not establish acceptance.

## Build from GitHub
1. Upload only the contents of the Clean GitHub Upload ZIP to the root of a GitHub repository (including `.github/workflows`).
2. Run `Actions > GRG-4361 FQC Windows Build > Run workflow`.
3. After the job succeeds, download the `GRG-4361-FQC-V1.0` artifact.
4. Extract, start EXE, enter router IP / username / password / DUT SN / approved FW, press `START READ-ONLY CHECK`.
5. After completion, inspect `Documents/GRG-4361_FQC_Records` and provide the sanitized logs when troubleshooting.

## Confidentiality
Do not share password, authentication cookies, CSRF tokens, raw HAR/cURL or personally identifying shipping data. The tool does not intentionally store login password, raw HTTP pages or cookies.
