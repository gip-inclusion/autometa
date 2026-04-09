#!/usr/bin/env python3
"""Pre-tool-use hook: enforce project Python conventions on Edit/Write."""

import json
import os
import re
import sys

SQL_KEYWORDS = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|SET|INTO|VALUES)\b", re.IGNORECASE)


def get_code_and_path(data):
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})
    path = inp.get("file_path", "")

    if not path.endswith(".py"):
        return None, None

    if tool == "Edit":
        return inp.get("new_string", ""), path
    if tool == "Write":
        return inp.get("content") or inp.get("file_content", ""), path
    return None, None


# -- Docstrings (rules/code.md) --


def check_docstrings(lines):
    violations = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        for quote in ('"""', "'''"):
            if stripped.startswith(quote):
                break
        else:
            i += 1
            continue

        # Bare closing triple-quote (""" alone or """) etc.) — not a docstring opening
        after = stripped[3:]
        if not after or (after[0] not in (" ", "\t") and not after[0].isalpha()):
            i += 1
            continue

        if stripped.count(quote) >= 2:
            if re.search(r"\b(Args|Returns|Examples|Parameters|Raises|Attributes)\s*:", stripped):
                violations.append(f"Docstring verbose (Args/Returns/Examples interdit): {stripped}")
            i += 1
            continue

        start = i
        i += 1
        while i < len(lines) and quote not in lines[i]:
            i += 1
        if i - start + 1 > 2:
            violations.append(f"Docstring multi-ligne interdit (max 1 ligne): {lines[start].strip()}")
        block = "\n".join(lines[start : i + 1])
        if re.search(r"\b(Args|Returns|Examples|Parameters|Raises|Attributes)\s*:", block):
            violations.append(f"Docstring verbose (Args/Returns/Examples interdit): {lines[start].strip()}")
        i += 1
    return violations


# -- Comments (rules/code.md) --


def check_comments(lines):
    violations = []
    for line in lines:
        stripped = line.strip()

        if re.match(r"^#\s*[-=*~]{3,}", stripped):
            violations.append(f"Commentaire délimiteur de section interdit: {stripped}")

        if re.match(
            r"^#\s*(def |class |import |from .+ import|return |yield |raise |"
            r"if __name__|for .+ in |while |with |try:|except |finally:)",
            stripped,
        ):
            if "noqa" not in stripped and "type:" not in stripped:
                violations.append(f"Code commenté interdit (supprimer si inutile): {stripped}")

    return violations


# -- Imports (rules/code.md, rules/tests.md) --


def check_imports(lines, path):
    violations = []
    for line in lines:
        stripped = line.strip()

        # unittest — pytest only (rules/tests.md)
        if re.match(r"^from unittest\.mock\b", stripped):
            violations.append(f"unittest.mock interdit — utiliser le fixture mocker de pytest-mock: {stripped}")
        elif re.match(r"^(from unittest|import unittest)", stripped):
            violations.append(f"unittest interdit — utiliser pytest: {stripped}")

        if re.match(r"^(import requests\b|from requests[\s.])", stripped):
            violations.append(f"requests interdit — utiliser httpx: {stripped}")

        if re.match(r"^(import urllib\.request|from urllib\.request|import urllib3|from urllib3)", stripped):
            violations.append(f"urllib interdit — utiliser httpx: {stripped}")

        # psycopg2 is only allowed in lib/data_inclusion.py (the SSH tunnel client itself)
        if re.match(r"^(import psycopg2|from psycopg2)", stripped) and "data_inclusion" not in path:
            violations.append(f"psycopg2 interdit — utiliser SQLAlchemy ou lib.data_inclusion: {stripped}")

        if re.match(r"^from \.\.", stripped):
            violations.append(f"Import relatif parent interdit — utiliser import absolu: {stripped}")

    return violations


# -- Environment variables (rules/code.md) --


def check_env_vars(lines, path):
    if path.endswith("config.py"):
        return []
    violations = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"os\.(getenv|environ\.get|environ\[)", stripped):
            violations.append(f"os.getenv/os.environ interdit hors config.py: {stripped}")
    return violations


# -- Exceptions (rules/code.md) --


def check_exceptions(lines):
    violations = []
    for i, line in enumerate(lines):
        stripped = line.strip()

        if re.match(r"^except\s*:", stripped):
            violations.append(f"except: nu interdit — spécifier l'exception: {stripped}")

        if re.match(r"^except\s+Exception\b", stripped) and "# Why:" not in stripped:
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if "# Why:" not in next_line:
                violations.append(f"except Exception sans '# Why:' interdit: {stripped}")

        if re.match(r"^except\b", stripped):
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if re.match(r"^pass\s*(#.*)?$", next_line):
                violations.append(
                    f"except/pass interdit — traiter l'exception (log, valeur par défaut, re-raise): {stripped}"
                )

    return violations


# -- SQL safety (rules/sql.md, rules/review.md) --


def _count_sql_keywords(s):
    return len(SQL_KEYWORDS.findall(s))


def check_sql(lines):
    violations = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        kw_count = _count_sql_keywords(stripped)

        # %s placeholder in SQL context (2+ keywords = real SQL)
        if "%s" in stripped and kw_count >= 2:
            violations.append(f"SQL avec %s interdit — utiliser text() avec :param nommés: {stripped[:120]}")

        # f-string with SQL interpolation (2+ keywords to avoid false positives on .update(), from e, etc.)
        if kw_count >= 2 and re.search(r"""\bf['"]{1,3}""", stripped) and "{" in stripped:
            violations.append(
                f"Interpolation SQL via f-string interdit — utiliser text() avec :param: {stripped[:120]}"
            )

        # .format() on SQL strings
        if ".format(" in stripped and kw_count >= 2:
            violations.append(
                f"Interpolation SQL via .format() interdit — utiliser text() avec :param: {stripped[:120]}"
            )

        # session.execute() with raw string instead of text()
        if re.search(r'\.execute\(\s*["\']', stripped) and kw_count >= 1:
            if "text(" not in stripped:
                violations.append(f'SQL brut sans text() interdit — utiliser text("...") ou l\'ORM: {stripped[:120]}')

    return violations


# -- API instantiation (rules/api.md) --


def check_api(lines):
    violations = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("#", "import", "from")):
            continue

        if re.search(r"\bMatomoAPI\s*\(", stripped):
            violations.append(
                f"MatomoAPI() direct interdit — utiliser lib.query.execute_matomo_query: {stripped[:120]}"
            )
        if re.search(r"\bMetabaseAPI\s*\(", stripped):
            violations.append(
                f"MetabaseAPI() direct interdit — utiliser lib.query.execute_metabase_query: {stripped[:120]}"
            )

    return violations


# -- httpx timeout (rules/code.md) --


def check_httpx_timeout(lines):
    violations = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # Match httpx.<method>( calls
        if not re.search(r"\bhttpx\.(get|post|put|patch|delete|head|options|request)\s*\(", stripped):
            continue

        # Check current line + next 5 lines for timeout=
        window = "\n".join(lines[i : i + 6])
        if "timeout" not in window:
            violations.append(f"httpx sans timeout= explicite interdit: {stripped[:120]}")

    return violations


# -- File naming (rules/code.md) --


def check_log_fstrings(lines):
    violations = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^logger\.(debug|info|warning|error|exception|critical)\(f['\"]", stripped):
            violations.append(
                f'f-string dans logger interdit (log injection) — utiliser logger.x("%s", var): {stripped[:120]}'
            )
    return violations


def check_file_name(path):
    basename = os.path.basename(path)
    if basename.startswith("_") and basename != "__init__.py":
        return [f"Fichier Python commençant par _ interdit (sauf __init__.py): {basename}"]
    return []


# -- Entrypoint --


def check(code, path):
    lines = code.split("\n")
    violations = []
    violations.extend(check_file_name(path))
    violations.extend(check_docstrings(lines))
    violations.extend(check_comments(lines))
    violations.extend(check_imports(lines, path))
    violations.extend(check_env_vars(lines, path))
    violations.extend(check_exceptions(lines))
    violations.extend(check_sql(lines))
    violations.extend(check_api(lines))
    violations.extend(check_httpx_timeout(lines))
    violations.extend(check_log_fstrings(lines))
    return violations


if __name__ == "__main__":
    data = json.load(sys.stdin)
    code, path = get_code_and_path(data)
    if code is None:
        sys.exit(0)

    violations = check(code, path)
    if violations:
        print("Violations des conventions Python du projet :\n", file=sys.stderr)
        for v in violations:
            print(f"  ✗ {v}", file=sys.stderr)
        print("\nRègle : .claude/rules/ — corrige avant de réessayer.", file=sys.stderr)
        sys.exit(2)
