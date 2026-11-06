# GRG-4361 FQC Test Tool V1.0.9

Windows 11 English GUI, Python 3.11 / GitHub Actions Windows build. No Python required on operator PC.

## New: Production Data TXT

An editable, **example-only** template is shipped as `GRG-4361_Production_Data_TEMPLATE.txt`. Replace placeholder customer PO, production MO, BOM, production quantity, SN/MAC ranges with QA-approved values **before use**. The sample must not be used to release production units.

1. Open tool and set **Operator**.
2. `Maintenance > Import Production Data TXT`, select edited TXT.
3. Import validates all required fields and confirms MO/BOM/PO/quantity; click Yes to activate.
4. The active MO / BOM / PO appear on the main screen; IP and FW populate automatically. Manual edits that disagree with imported values prevent starting.
5. Barcode scans, two-step LED verification, HTTP, Telnet and O5/optics proceed as before.
6. `Maintenance > View Active Production Data`, `Export Active Production TXT` or `Switch to Manual Settings` as needed.
7. `Maintenance > Production Range Settings` remains available for manual mode. For manual testing, deactivate an imported lot first; changing the manual range does not change any imported lot.

Never include a router password in TXT. Router credential is set once per Windows account in `Maintenance > Set Router Credential` using Windows Credential Manager.

## Records

All files live beneath `<EXE folder>/Records`. Every test has its own `result.json`, `FQC_Result.xlsx`, `execution.log`, `test.log`, `debug.log` (except early unrecoverable errors, which may not yield an Excel). The EXE folder must be writable.

The Master `GRG-4361_FQC_Master_Record.xlsx` maintains append-only `All Tests` and numeric `Summary`, and adds `Production Info` and `Lot History`. Per-test snapshots bind the production data / SHA-256 to that DUT even after lot changes. The original imported TXT is copied to `Records/Production_Snapshots/<sha256>.txt`. Note: `Lot History` is reconstructed from completed tests; imported-but-unused lots only have their snapshots.

Close the Master workbook in Excel before running or syncing. If locked, run data remains available as individual JSON records. `Maintenance > Sync Master` retries safely without duplicate run IDs.

The import checks SN numeric suffix interval, MAC allocation capacity assuming 4 consecutive MACs per DUT, and valid field formats. **This does not establish the factory's base-MAC allocation stride**. Confirm stride with the official allocation plan before approving use.

## Existing test standards remain in code

PON Tx: 6.8–7.2 dBm inclusive; ONU O5 within 10 seconds; BID length 20 with consecutive PPP; three WAN golden settings; two manual LED steps. The imported TXT only selects a test profile name and version for traceability; it **cannot override** these quality limits. The profile identifier is not an external approval/signature mechanism.

## Build

Unzip the Clean GitHub package (including hidden `.github` directory) to the repository root, open Actions > GRG-4361 FQC Windows Build > Run workflow, and download its V1.0.9 artifact. GitHub and US Windows 11 field validation are required before production release.
