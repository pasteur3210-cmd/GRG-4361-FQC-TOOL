# Changelog

## V1.0.6 (2026-11-05)
- Added maintenance-only Production Range Settings for SN Start/End, MAC Start/End and MACs per DUT (default 4).
- Added 20-character SN suffix-range comparison, MAC range/allocation-boundary check and historical SN/MAC collision detection (same SN+MAC can be retested).
- Added Windows Credential Manager-backed root login: provision once via Maintenance > Set Router Credential. Operators do not enter credentials for every DUT; password is not embedded in code or logs.
- Functional LED instruction explicitly requires Power LED blue solid, Phone LED green blinking, PON LED green solid.
- Preserved read-only HTTP, O5 maximum 10 seconds, optical Tx 6.8–7.2 dBm, per-run reports, and accumulating Master Record.
- Pending: confirm factory MAC base-address increment/allocation policy before production release. Sequential four-MAC allocation used as a provisional check.
