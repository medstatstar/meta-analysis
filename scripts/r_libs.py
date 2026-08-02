#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
r_libs.py -- shared R execution / validation / sanitization layer for the ct- skill library.

Provides generic, security-hardened helpers that EVERY R-backed ct- skill reuses:

  - find_rscript() / is_valid_rscript()
        Locate the Rscript binary and verify it is genuinely Rscript (prevents
        binary substitution / RCE via a swapped executable).
  - _validate_token() / _safe_r_path_literal()
        Allowlist validation of every user string that reaches generated R, so a
        user value can NEVER break out of an R string literal and inject code.
  - sanitize_output()
        Strip file paths and truncate before any output is shown to the user.
  - run_r(code, confirmed=False, preamble="")
        Execute R safely. OFF by default (returns a dry-run notice); opt in with
        confirmed=True. `preamble` lets a business skill inline its own domain R
        source (e.g. a localization helper) ahead of the generated code.

This module is intentionally business-agnostic. Domain-specific R source strings
(sample-size engines, i18n.R, adaptive-trial simulators, ...) live in each ct-
skill (e.g. ct-samplesize), NEVER here -- so a freshly copied skill starts clean.
"""

import os
import re
import sys
import textwrap
import subprocess
import tempfile

from i18n import t


# ═══════════════════════════════════════════════════════════════════════════
# Security: strict validation of EVERY user string that reaches generated R
# ═══════════════════════════════════════════════════════════════════════════
# Goal: make it impossible for a user-supplied value to break out of an R string
# literal and inject arbitrary R code (RCE). Generated R embeds user values
# inside single- or double-quoted literals, so we reject any value containing
# characters that could terminate the string or start a new R statement.
#
# _SAFE_TOKEN_RE : for short categorical tokens (option names, design names, ...)
# _SAFE_PATH_RE  : for filesystem paths (allows separators, spaces, CJK names)
_SAFE_TOKEN_RE = re.compile(r'^[A-Za-z0-9_\-]+$')
_SAFE_PATH_RE = re.compile(r'^[A-Za-z0-9_.\- /\\:一-鿿]+$')


def find_rscript():
    """Locate the Rscript executable (env override, PATH lookup, then known paths)."""
    env_path = os.environ.get("RSCRIPT_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    from shutil import which
    path = which("Rscript")
    if path:
        return path
    defaults = [
        r"C:\Tools\R-4.5.1\bin\x64\Rscript.exe",
        r"C:\Program Files\R\R-4.5.1\bin\x64\Rscript.exe",
        "/usr/local/bin/Rscript",
        "/usr/bin/Rscript",
    ]
    for d in defaults:
        if os.path.isfile(d):
            return d
    return None


def is_valid_rscript(path):
    """Ensure the resolved executable is genuinely Rscript (prevent binary substitution).

    Audit hardening: the caller runs generated R code via subprocess, so we must
    guarantee the binary we invoke is the real Rscript, not an attacker-supplied
    executable, and that it is actually executable.
    """
    if not path or not os.path.isfile(path):
        return False
    try:
        real = os.path.realpath(path)
    except OSError:
        return False
    base = os.path.basename(real).lower()
    if base not in ("rscript", "rscript.exe"):
        return False
    if not os.access(real, os.X_OK):
        return False
    return True


def _validate_token(name, value):
    """Reject categorical string args that could break out into R code."""
    if value is None:
        return value
    if not _SAFE_TOKEN_RE.match(value):
        raise ValueError(
            "Invalid %s=%r: only [A-Za-z0-9_-] allowed "
            "(no quotes, semicolons or parentheses)." % (name, value)
        )
    return value


def _safe_r_path_literal(path):
    """Return `path` safely embedded in an R string literal, or None if absent.

    Validates against a path allowlist, then normalises Windows separators to
    forward slashes (R accepts them on every platform). Raises ValueError on any
    value that could escape the R string context.
    """
    if path is None:
        return None
    if not _SAFE_PATH_RE.match(path):
        raise ValueError(
            "Unsafe output path %r: only letters, digits, spaces and ._-:/\\ "
            "are allowed (no quotes, semicolons or parentheses)." % path
        )
    return path.replace("\\", "/")


def sanitize_output(raw, max_lines=200, max_col=200):
    """Strip file paths and truncate output before showing it to the user."""
    cleaned = re.sub(
        r'[A-Za-z]:\\(?:[^\s:"\']+\\)*[^\s:"\']+|/(?:[^\s:"\']+/)+[^\s:"\']+',
        lambda m: os.path.basename(m.group(0)), raw
    )
    lines = cleaned.split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f'... ({len(lines) - max_lines} lines truncated)']
    lines = [
        textwrap.shorten(l, width=max_col, break_long_words=False, placeholder='…')
        if len(l) > max_col else l for l in lines
    ]
    return '\n'.join(lines)


def run_r(code, confirmed=False, preamble=""):
    """Execute R `code` (OFF by default) or return a safe-preview message.

    Args:
        code: R source to run.
        confirmed: when False, returns a dry-run notice and does NOT execute.
            Set True to actually run (the --yes / safe-preview opt-in pattern).
        preamble: optional R source prepended before `code` (e.g. a business
            skill's inlined localization helper). Kept empty in this base layer;
            domain strings are passed by the calling skill, not stored here.

    Returns:
        Localized stdout/stderr (sanitized), or a localized notice string.
    """
    if not confirmed:
        return t("dry_run.not_executed")
    rscript = find_rscript()
    if not is_valid_rscript(rscript):
        return t("error.rscript_not_found")

    # RCE prevention: user strings are allowlist-validated before they reach
    # generated R (see _validate_token / _safe_r_path_literal); the generated
    # code therefore cannot contain sandbox-escape tokens.

    # Neutralize any leftover source() placeholder from a business template
    # (publishing strips .R files, so the inline `preamble` must supply it).
    code = code.replace('source(file.path("{scriptdir}", "i18n.R"))', '# i18n.R inlined')

    # Use the system temp dir so no residue is left if the process is killed.
    tmp_dir = os.path.realpath(tempfile.gettempdir())
    body = "options(echo = FALSE)\n"
    if preamble:
        body += preamble + "\n"
    body += code
    with tempfile.NamedTemporaryFile(
        suffix='.R', mode='w', delete=False, encoding='utf-8', dir=tmp_dir
    ) as f:
        f.write(body)
        tmp = f.name

    # Containment: the script must live inside the system temp dir.
    if os.path.dirname(os.path.realpath(tmp)) != tmp_dir:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return t("error.invalid_temp_path")

    # NOTE: invoked as a list (no shell), so no command/shell injection is possible.
    try:
        proc = subprocess.run(
            [rscript, '--vanilla', tmp],
            capture_output=True, text=True, timeout=300
        )
        raw = (proc.stdout or '') + (proc.stderr or '')
        return sanitize_output(raw)
    except subprocess.TimeoutExpired:
        return t("error.r_timeout")
    except Exception as e:
        return t("error.exec_failed", name=type(e).__name__)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
