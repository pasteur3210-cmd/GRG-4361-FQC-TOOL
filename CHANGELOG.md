# Changelog

## V1.0.9
- Added validated key=value Production Data TXT import, lot activation, SHA-256 snapshots and active-lot display.
- Manual and TXT modes; immutable run-level lot snapshot, no automatic test-standard overrides.
- All Tests expanded with customer PO, BOM, MO, IP, profile and SN/MAC ranges.
- Master Production Info and Lot History generated from completed run records; Summary now stores numeric totals rather than formula-only cached blanks.
- Added import failure protection, production-lot mismatched IP/FW blocking, and in-test lot-switch prevention.
- Retained V1.0.8 HTTP, Telnet, WAN, LED, O5, Tx-power, FAIL UI, report and log logic.

## V1.0.11 (2026-11-17)
- Remove 15 mostly empty production-detail columns from `All Tests`; keep LAN1 and FXS actual inspection results.
- Keep production lot details under `Production Info` and `Lot History`, preserving per-run Production Data snapshots.
- Migrate older wide Master Record files by matching column headers rather than copying cells by fixed position.
- Retain existing `All Tests` attempt history and Retest No. values when converting.
- Preserve Summary's directly calculated PASS/FAIL/REVIEW/ERROR numbers.
- No changes to HTTP login, LAN1 10G, FXS, Telnet BID, ONU O5, Tx Power, or FQC judgment rules.
- HTTP timeout caused by a disconnected network cable remains a connectivity/fixture error, not a DUT failure.

# Changelog

## V1.0.9
- Added validated key=value Production Data TXT import, lot activation, SHA-256 snapshots and active-lot display.
- Manual and TXT modes; immutable run-level lot snapshot, no automatic test-standard overrides.
- All Tests expanded with customer PO, BOM, MO, IP, profile and SN/MAC ranges.
- Master Production Info and Lot History generated from completed run records; Summary now stores numeric totals rather than formula-only cached blanks.
- Added import failure protection, production-lot mismatched IP/FW blocking, and in-test lot-switch prevention.
- Retained V1.0.8 HTTP, Telnet, WAN, LED, O5, Tx-power, FAIL UI, report and log logic.

