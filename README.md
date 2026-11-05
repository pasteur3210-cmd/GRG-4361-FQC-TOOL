# GRG-4361 FQC Test Tool V1.0.6

English Windows 11 FQC read-only testing utility. Build EXE via GitHub Actions; Python is not required on factory workstations.

## Setup (once per Windows account)
1. Extract EXE to a writable folder. Start it.
2. In **Maintenance > Set Router Credential**, enter the approved root account password. It is saved via the OS credential provider; the secret is not stored in source or in Records. Do not share the password in logs.
3. In **Maintenance > Production Range Settings**, enter approved 20-character SN first/last, MAC first/last, and MAC quantity per DUT (default 4). Settings file is `Records/production_range.json`. Verify the allocation step with your factory before production release.
4. Fill Approved FW and Operator. Scan Chassis Label SN, MAC and GPON SN. Click START READ-ONLY CHECK.
5. Confirm initial LEDs: Power green, Phone off, LAN blue where qualified, PON red blink. Connect fiber and off-hook telephone, then confirm Phone green blink, PON green solid, **Power blue solid**. Operator decision is required.
6. Only after functional LED confirmation will the tool read device/PON information, check ONU O5 (10 s maximum), and evaluate optical Tx 6.8–7.2 dBm.

## Results
A separate `Records/<timestamp>/FQC_Result.xlsx` is saved for every run with `execution.log`, `test.log`, `debug.log`, `result.json`. All completed runs append into `Records/GRG-4361_FQC_Master_Record.xlsx`, preserving retests. Maintenance menu opens records and syncs pending runs.

## Range semantics
- SNs must share a fixed prefix and fixed-width decimal suffix; full SN length 20. Inclusive start/end.
- MAC may be scanned with or without colons. Check lower/upper inclusive allocation based on base MAC through base+quantity-1. This assumes consecutive MAC assignments and **must be reconciled against factory MAC allocation rules**.
- Missing approved ranges produce REVIEW (not PASS), out-of-range items FAIL.
- Conflicting SN/MAC identities in previous runs FAIL; a repeat of the same SN and MAC is allowed and retained as a retest.

## Test / build
`python -m pip install -r requirements.txt`
`python -m pytest -q tests`
`pyinstaller --noconfirm --clean GRG-4361_FQC.spec`

Windows Credential Manager via `keyring` must be verified after building with GitHub Actions. If the provider cannot store a secret, the application displays an error rather than exposing or caching a plaintext password. PyInstaller and target Windows 11 English verification are pending.
