# CHANGELOG
## V1.0.7 — 2026-11-05
- Added read-only Telnet BID verification (`labelinfo`) with 20-character length and contiguous `PPP` checks.
- Added large colored overall-status banner, per-row PASS/FAIL/REVIEW/ERROR shading, and Failure / Error Summary with expected and actual values.
- Removed three `WAN Link nas0_0/1/2` INFO test rows from GUI, single-run report and new test results; retained underlying WAN parser and legacy Master columns for audit compatibility.
- Appended PON BID and both BID results to the cumulative Master Record.
- Preserved V1.0.6 features: barcode scan, LED checks, SN/MAC range, O5 timeout 10 s, Tx 6.8–7.2 dBm, one-run Excel, master append and three logs.
