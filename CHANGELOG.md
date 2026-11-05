# V1.0.5 (2026-11-05)
- Reduced O5 state polling window from 60 s to 10 s, cadence 2 s to 1 s.
- When O5 times out, record explicit O5 Timeout FAIL, Tx Power SKIP, save single-unit and Master records; keep GUI running.
- Preserve 6.8–7.2 dBm optical Tx threshold, barcodes, two LED manual checks, existing HTTP read-only workflow.
- Updated workflow, EXE filename, docs and regression tests.

# CHANGELOG
## V1.0.4 — 2026-11-05
- Three mandatory barcode entry fields: SN, MAC, GPON SN. Automatic focus advance on scanner Enter.
- Two-step manual LED checks: initial LED states then handset/fiber/O5 functional states. PASS focus, explicit acceptance required. FAIL stops HTTP operation and logs the result.
- Two-stage HTTP ordering: read Device and GPON identity after confirmed fiber setup; poll PON state only after this point. O5 required, max 60-second polling.
- Added PON Tx Power check 6.8–7.2 **dBm**, provisional unit subject to user confirmation; reject unrecognized units and No signal.
- Label MAC vs DUT MAC, Label GPON SN vs DUT GPON SN and GPON SN vs MAC cross-checks.
- Simplified production GUI to single START button; maintenance actions moved to menu.
- Master Record upgraded in place to retain V1.0.3 rows and append label/LED/Tx results.
- Expanded tests to 23 passing scenarios (local; real DUT/OLT and GitHub Actions EXE unverified).
## V1.0.3
- Retained per-run Excel/Log and cumulative Master.
