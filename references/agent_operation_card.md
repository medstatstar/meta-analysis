# Agent operation card (copy verbatim, no variations)

> Compute-track one-shot card. Migrated out of `SKILL.md` §0 on 2026-10-20 per
> ct-base `docs/01-spec-scaffold.md` §4 (SKILL.md is not a CLI document; audit
> P2-1). The **topic track does NOT use this card**.

```bash
# Compute track one-shot: report lands in --out-dir (user workspace); in-conversation data uses --data-json to skip file writes.
# If data comes from a file, pass --data <csv|json absolute path> (csv auto-converts to JSON before sending to coze).
python scripts/run_meta.py --query "<user original request>" --data-json '<[{"study":"S1",...}]>' --out-dir "<user workspace>/meta_analysis"
```

Read `META_HTML_REPORT=<path>` from stdout and pass directly to `present_files`; across turns, carve a subset into a new csv/json and re-issue the same command (always include `--out-dir`). Do NOT use this card for the topic track. Fallback `META_STATUS=build_failed` → re-run with `--colmap` per the hint.
