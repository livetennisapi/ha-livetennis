# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] — 2026-08-07

### Added
- **Re-authentication flow**: when the API key is revoked or disabled (401),
  Home Assistant now prompts for a replacement key instead of failing with an
  unknown-step error. Fixes the pre-existing reauth test failure at its root.
- **`abuse_throttled` handling**: a 429 `abuse_throttled` response (key blocked
  for chronic over-quota use, typically 24 h) now pauses polling until the
  server's `retry_at_epoch`, logs a clear warning, and raises a repair issue in
  Settings → Repairs. Polling cadence and the repair reset automatically once
  the API serves data again. Ordinary minute/day 429s remain transient.
- `scripts/truthcheck.sh` + a CI workflow (pytest against the Home Assistant
  test harness, plus the truth pin) alongside the existing hassfest/HACS
  validation.
- CHANGELOG (this file).

### Changed
- README brought to the org fleet standard: badges, current quota grid
  (2026-08-06: FREE 100/day, BASIC 1,000/day, PRO 10,000/day, ULTRA
  500,000/day), tier note for the one endpoint used, auth section, links block.
  The per-tour quota arithmetic tables are unchanged.
- License holder and manifest codeowners now use the Live Tennis API org
  identity.

## [1.0.2] — 2026-08-06

### Changed
- Quota copy and safe defaults for the 2026-08-06 quota grid: free tier is
  100 requests/day; default update interval raised to 900 s so the common
  setups (no tour filter, or one tour) fit a free key; per-tour interval
  guidance documented.
- Corrected repo URLs and documented the real free-tier daily quota math.

## [1.0.1] — 2026-07-24

### Added
- Brand icons shipped in the integration.

### Fixed
- Signup URL passed as a description placeholder (hassfest forbids literal
  URLs in translated strings).

## [1.0.0] — 2026-07-24

### Added
- Initial release: HACS custom integration with a live-match count sensor and
  per-match score sensors via a DataUpdateCoordinator, config + options flow,
  tour filtering, and real-Home-Assistant tests.
