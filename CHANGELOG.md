# Changelog / 变更日志

All notable changes to the `meta-analysis` skill are recorded here. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — 2026-08-02

### Added / 新增
- **ct-base alignment**: comprehensive alignment with `ct-base` BASE.md specification.
  - Added `AGENTS.md` (English-only agent-facing rules: environment, execution, language, security, reuse, menu triage, traceability).
  - Added `CHANGELOG.md` (this file).
  - Added `references/units.md` (atomic task unit index for pipeline).
  - Added `scripts/i18n.py` (from ct-base — bilingual EN/ZH helper with auto locale detection).
  - Added `scripts/r_libs.py` (from ct-base — R invocation + validation + sanitization helper).
  - Added `references/language_policy.md` (from ct-base — detailed bilingual policy).
  - Added `references/report_template.md` (from ct-base — report skeleton reference).

### Changed / 变更
- **SKILL.md**: frontmatter enriched with `required_commands: [Rscript, python]`. Body remains English-only agent-facing.
- **README files**: renamed `README_ZH.md` → `README_zh-CN.md` per ct-base naming convention.
- **Language detection**: migrated to `i18n.py`'s unified `is_chinese_os()` (covers env vars + Windows API + Python locale fallback).

### Fixed / 修复
- Removed stale `README_ZH.md` references across SKILL.md, README.md, README_zh-CN.md.

---

## [1.7.0] — 2026-08-01

### Added / 新增
- Full bilingual auto-switch: default English, auto-switch to Chinese on `zh-*` locale (`.msg(en, zh)` pattern in R files + Python i18n).
- `permissions` block declaration in SKILL.md frontmatter.
- `references/svg_editing.md` — SVG editing tools & journal format conversion guide.
- `references/advanced_api.md` — reusable API reference for TSA / dose-response / survival / Bayesian NMA wrappers.

### Changed / 变更
- Effect size conversion module (`esc`) expanded: d ↔ g ↔ logOR ↔ r ↔ Fisher's z, batch mode + Hedges' g correction.

---

## [1.6.0] — 2026-07-25

### Added / 新增
- Bayesian NMA: `multinma` (Stan) + `gemtc` (JAGS) full workflows.
- TSA: self-implemented `run_tsa()` with O'Brien-Fleming boundaries.
- Survival meta: `survmeta` wrapper + KM pseudo-IPD reconstruction.
- Dose-response: `dosresmeta` wrapper.

---

## [1.5.0] — 2026-07-15

### Added / 新增
- Initial public release on GitHub / ClawHub / SkillHub.
- Full RevMan 5.x 1:1 code mapping.
- Stata `metareg` / `mvmeta` equivalents.
- Network meta: `netmeta` + `gemtc` + `multinma`.
- Single-group meta: `metaprop` / `metamean` / `metainc` / `metacor`.
- Diagnostic meta: `mada::reitsma` bivariate + SROC.

---

## [1.0.0] — 2026-06-01

### Added / 新增
- Initial version. Core pairwise meta-analysis with `metafor` / `meta`.
