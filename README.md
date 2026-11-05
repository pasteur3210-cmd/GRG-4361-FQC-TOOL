# GRG-4361 FQC Test Tool V1.0.7

**Operating system:** Windows 11 x64 English; **build:** GitHub Actions, Python 3.11 and PyInstaller. End users do not install Python.

## Operation
1. Copy the EXE to a writable folder; place records under `Records` alongside EXE.
2. From `Maintenance > Set Router Credential`, store the router password once per Windows user. Username is fixed `root`. No plaintext password is embedded in source.
3. Under `Maintenance > Production Range Settings`, set approved SN/MAC ranges and MAC count (default four). Confirm the allocation stride against factory data.
4. Scan chassis-label SN, MAC and GPON SN. Confirm initial and functional LED checks with the operator.
5. Connect optical fiber, allow OLT registration, click the read-only test. O5 must appear within 10 seconds. Read Tx Power only after O5; 6.8–7.2 dBm is PASS.
6. V1.0.7 also establishes Telnet on TCP 23, logs in with the same Windows-protected credential, executes only `labelinfo`, parses `PON BID`, checks 20 characters and consecutive `PPP`.
7. Check the large colored status banner and Failure / Error Summary. Each failing row shows the expected and actual values. Three WAN Link Status-only test items are removed. WAN configuration items remain.
8. Each test saves `FQC_Result.xlsx`, `result.json`, `execution.log`, `test.log`, `debug.log` under a timestamped Records folder. `GRG-4361_FQC_Master_Record.xlsx` appends all attempts. Access maintenance tools from the menu.

## Important boundaries
- Device configuration is not changed; only HTTP reads and Telnet `labelinfo`.
- Telnet sends the credential over plaintext TCP. Use only on an isolated, authorized factory test LAN; never across the internet.
- BID failure is FAIL; Telnet connection/parse failure is ERROR. The other device checks and result journal are retained where possible.
- Prior Master columns are preserved for backward compatibility; three new BID columns are appended. New single-unit reports and GUI no longer include WAN Link Status as independent test items.
- A fully populated Master workbook cannot be simultaneously opened for writing in Excel. Close it and use Maintenance > Sync Master to retry.
- Python parser and Telnet protocol receive tests are simulated. GitHub Actions build, physical Telnet login, OLT and US Windows 11 execution are NOT yet verified.
