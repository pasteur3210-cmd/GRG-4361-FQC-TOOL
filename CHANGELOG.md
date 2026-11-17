# Changelog

## V1.0.9
- Added validated key=value Production Data TXT import, lot activation, SHA-256 snapshots and active-lot display.
- Manual and TXT modes; immutable run-level lot snapshot, no automatic test-standard overrides.
- All Tests expanded with customer PO, BOM, MO, IP, profile and SN/MAC ranges.
- Master Production Info and Lot History generated from completed run records; Summary now stores numeric totals rather than formula-only cached blanks.
- Added import failure protection, production-lot mismatched IP/FW blocking, and in-test lot-switch prevention.
- Retained V1.0.8 HTTP, Telnet, WAN, LED, O5, Tx-power, FAIL UI, report and log logic.

## V1.0.10 (2026-11-17)
- Add read-only HTTP `/lan_port_status.asp` LAN1 actual link status check: `Up, 10Gb, Full` is PASS; speed, link, or duplex mismatch is FAIL; unreadable page is ERROR.
- Update LAN HTML parser for a single GRG-4361 LAN1 (10GE) row and Gb/Gbps vs Mbps units. Ignore selectable link-mode options.
- Add separate FXS result based on the Step 2 off-hook Phone LED visual confirmation, without introducing telephony audio testing. Step 2 offers a Phone LED PASS/FAIL choice.
- Extend single DUT results, master workbook, test/debug logs and GUI Failure Summary with LAN1 and FXS results.
- Maintain the prior HTTP, Telnet BID, O5, Tx Power, LED and production TXT rules.
