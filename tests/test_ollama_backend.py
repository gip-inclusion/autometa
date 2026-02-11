"""
Tests for the Ollama backend: ollama.py, ollama_tools.py, llm.py.

Split into two sections:
1. Bug-finding tests (xfail) — confirmed defects not yet fixed
2. Coverage tests — meaningful behavior verification

Run with: pytest tests/test_ollama_backend.py -v
"""

import importlib
import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module loading: same stub trick as test_ollama_tools.py to avoid
# importing Flask/SDK which aren't available in CI.
# ---------------------------------------------------------------------------

_web_stub = sys.modules.get("web") or types.ModuleType("web")
_web_stub.__path__ = ["web"]
_agents_stub = sys.modules.get("web.agents") or types.ModuleType("web.agents")
_agents_stub.__path__ = ["web/agents"]
sys.modules.setdefault("web", _web_stub)
sys.modules.setdefault("web.agents", _agents_stub)

# Load web.config
if "web.config" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("web.config", "web/config.py")
    _config_mod = importlib.util.module_from_spec(_spec)
    sys.modules["web.config"] = _config_mod
    _web_stub.config = _config_mod
    _spec.loader.exec_module(_config_mod)
config = sys.modules["web.config"]

# Load web.agents.ollama_tools
if "web.agents.ollama_tools" not in sys.modules:
    _spec2 = importlib.util.spec_from_file_location("web.agents.ollama_tools", "web/agents/ollama_tools.py")
    _tools_mod = importlib.util.module_from_spec(_spec2)
    sys.modules["web.agents.ollama_tools"] = _tools_mod
    _spec2.loader.exec_module(_tools_mod)
else:
    _tools_mod = sys.modules["web.agents.ollama_tools"]

# Stub httpx and base module before loading ollama.py
_httpx_stub = sys.modules.get("httpx") or types.ModuleType("httpx")
_httpx_stub.AsyncClient = type("AsyncClient", (), {
    "__init__": lambda *a, **kw: None,
    "is_closed": property(lambda s: False),
})
_httpx_stub.ConnectError = type("ConnectError", (Exception,), {})
_httpx_stub.ReadTimeout = type("ReadTimeout", (Exception,), {})
_httpx_stub.Client = type("Client", (), {"__init__": lambda *a, **kw: None})
_httpx_stub.HTTPError = type("HTTPError", (Exception,), {})
sys.modules.setdefault("httpx", _httpx_stub)

_base_stub = sys.modules.get("web.agents.base") or types.ModuleType("web.agents.base")
_base_stub.AgentBackend = type("AgentBackend", (), {})
_base_stub.AgentMessage = type("AgentMessage", (), {
    "__init__": lambda self, **kw: self.__dict__.update(kw),
    "__repr__": lambda self: f"AgentMessage({self.__dict__})",
})
sys.modules.setdefault("web.agents.base", _base_stub)

# Load web.agents.ollama
if "web.agents.ollama" not in sys.modules:
    _spec3 = importlib.util.spec_from_file_location("web.agents.ollama", "web/agents/ollama.py")
    _ollama_mod = importlib.util.module_from_spec(_spec3)
    sys.modules["web.agents.ollama"] = _ollama_mod
    _spec3.loader.exec_module(_ollama_mod)
else:
    _ollama_mod = sys.modules["web.agents.ollama"]

# Load web.llm
if "web.llm" not in sys.modules:
    _spec4 = importlib.util.spec_from_file_location("web.llm", "web/llm.py")
    _llm_mod = importlib.util.module_from_spec(_spec4)
    sys.modules["web.llm"] = _llm_mod
    _spec4.loader.exec_module(_llm_mod)
else:
    _llm_mod = sys.modules["web.llm"]

# Convenient references
_trim_history = _ollama_mod._trim_history
_should_stream_text = _ollama_mod._should_stream_text
_should_flush_buffer = _ollama_mod._should_flush_buffer
_chunk_text = _ollama_mod._chunk_text
_bash_allowed = _tools_mod._bash_allowed
_read_file = _tools_mod._read_file
_write_file = _tools_mod._write_file
_edit_file = _tools_mod._edit_file
_glob_files = _tools_mod._glob_files
_grep_files = _tools_mod._grep_files
_run_bash = _tools_mod._run_bash
_read_skill = _tools_mod._read_skill
_truncate = _tools_mod._truncate
_resolve_path = _tools_mod._resolve_path
_is_within = _tools_mod._is_within
parse_tool_call = _tools_mod.parse_tool_call
execute_tool = _tools_mod.execute_tool
tool_protocol = _tools_mod.tool_protocol


# ===================================================================
# SECTION 1: Regression tests for fixed Ollama bugs
# ===================================================================


class TestBashAllowedPrefixBoundary:
    """Fixed: prefix match now enforces a word boundary (space or end)."""

    def test_python_prefix_does_not_match_python3(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(python:*)")
        assert _bash_allowed("python3 evil.py") is False

    def test_curl_prefix_does_not_match_curly(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(curl:*evil.com*)")
        assert _bash_allowed("curly https://evil.com") is False

    def test_python_prefix_still_matches_python(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(python:*)")
        assert _bash_allowed("python script.py") is True

    def test_exact_prefix_no_args(self, monkeypatch):
        """Command that IS the prefix with no trailing args."""
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(python:)")
        assert _bash_allowed("python") is True


class TestTrimHistoryEdgeCases:
    """Fixed: oversized single message is now truncated instead of dropped."""

    def test_single_oversized_message_returns_truncated(self):
        history = [
            {"role": "user", "content": "x" * 60000},
        ]
        result = _trim_history(history, max_chars=50000)
        assert len(result) == 1
        assert len(result[0]["content"]) == 50000

    def test_oversized_only_drops_old_not_recent(self):
        history = [
            {"role": "user", "content": "old " * 10000},      # 40k
            {"role": "assistant", "content": "recent " * 10000},  # 70k
        ]
        result = _trim_history(history, max_chars=50000)
        # Should keep the most recent message (truncated), drop the old one
        assert len(result) >= 1
        assert result[-1]["role"] == "assistant"


class TestOllamaGenerateTimeoutZero:
    """Fixed: timeout=0 is preserved (was treated as falsy)."""

    def test_timeout_zero_is_preserved(self, monkeypatch):
        monkeypatch.setattr(config, "OLLAMA_REQUEST_TIMEOUT", 120)
        monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://fake:11434")

        captured = {}

        def fake_post(self_or_url, *a, **kw):
            resp = MagicMock()
            resp.json.return_value = {"response": "ok", "done": True}
            resp.raise_for_status = MagicMock()
            return resp

        def capture_init(self, *a, **kw):
            captured["timeout"] = kw.get("timeout")

        _httpx_stub.Client = type("Client", (), {
            "__init__": capture_init,
            "post": fake_post,
            "close": lambda self: None,
        })

        try:
            _llm_mod._ollama_generate(
                "test",
                model="test",
                max_tokens=10,
                temperature=0.2,
                timeout=0,
                client=None,
            )
        finally:
            _httpx_stub.Client = type("Client", (), {"__init__": lambda *a, **kw: None})

        assert captured.get("timeout") == 0

    def test_timeout_none_uses_config_default(self, monkeypatch):
        monkeypatch.setattr(config, "OLLAMA_REQUEST_TIMEOUT", 99)
        monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://fake:11434")

        captured = {}

        def fake_post(self_or_url, *a, **kw):
            resp = MagicMock()
            resp.json.return_value = {"response": "ok", "done": True}
            resp.raise_for_status = MagicMock()
            return resp

        def capture_init(self, *a, **kw):
            captured["timeout"] = kw.get("timeout")

        _httpx_stub.Client = type("Client", (), {
            "__init__": capture_init,
            "post": fake_post,
            "close": lambda self: None,
        })

        try:
            _llm_mod._ollama_generate(
                "test",
                model="test",
                max_tokens=10,
                temperature=0.2,
                timeout=None,
                client=None,
            )
        finally:
            _httpx_stub.Client = type("Client", (), {"__init__": lambda *a, **kw: None})

        assert captured.get("timeout") == 99


class TestWriteFileEmptyContent:
    """Fixed: _write_file now returns 'Missing content' when content is omitted."""

    def test_missing_content_field_returns_error(self, tmp_path):
        path = tmp_path / "target.txt"
        result = _write_file({
            "file_path": str(path),
            # "content" intentionally omitted
        })
        assert "Missing" in result
        assert not path.exists()

    def test_explicit_empty_content_still_works(self, tmp_path):
        """Explicitly passing content="" is intentional — should succeed."""
        path = tmp_path / "target.txt"
        result = _write_file({
            "file_path": str(path),
            "content": "",
        })
        assert "Wrote" in result
        assert path.exists()


# ===================================================================
# SECTION 2: Coverage tests — meaningful behavior verification
# ===================================================================


# -- _trim_history --------------------------------------------------


class TestTrimHistory:
    def test_empty_history(self):
        assert _trim_history([], max_chars=1000) == []

    def test_all_messages_fit(self):
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = _trim_history(history, max_chars=1000)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_trims_oldest_first(self):
        history = [
            {"role": "user", "content": "a" * 100},      # oldest
            {"role": "assistant", "content": "b" * 100},   # middle
            {"role": "user", "content": "c" * 100},        # most recent
        ]
        result = _trim_history(history, max_chars=250)
        # Should keep the 2 most recent messages (200 chars) and drop oldest
        assert len(result) == 2
        assert result[0]["content"].startswith("b")
        assert result[1]["content"].startswith("c")

    def test_zero_max_chars_returns_empty(self):
        history = [{"role": "user", "content": "hello"}]
        assert _trim_history(history, max_chars=0) == []

    def test_negative_max_chars_returns_empty(self):
        history = [{"role": "user", "content": "hello"}]
        assert _trim_history(history, max_chars=-1) == []

    def test_preserves_message_order(self):
        history = [
            {"role": "user", "content": "1"},
            {"role": "assistant", "content": "2"},
            {"role": "user", "content": "3"},
        ]
        result = _trim_history(history, max_chars=1000)
        contents = [m["content"] for m in result]
        assert contents == ["1", "2", "3"]

    def test_drops_extra_fields(self):
        """Only role and content are kept for Ollama."""
        history = [
            {"role": "user", "content": "hi", "timestamp": 123, "metadata": {}},
        ]
        result = _trim_history(history, max_chars=1000)
        assert set(result[0].keys()) == {"role", "content"}


# -- _chunk_text ----------------------------------------------------


class TestChunkText:
    def test_empty_string(self):
        assert _chunk_text("", 10) == [""]

    def test_exact_chunk_size(self):
        assert _chunk_text("abcde", 5) == ["abcde"]

    def test_multiple_chunks(self):
        assert _chunk_text("abcdef", 2) == ["ab", "cd", "ef"]

    def test_remainder_chunk(self):
        assert _chunk_text("abcde", 2) == ["ab", "cd", "e"]

    def test_zero_size_returns_whole(self):
        assert _chunk_text("abc", 0) == ["abc"]

    def test_negative_size_returns_whole(self):
        assert _chunk_text("abc", -1) == ["abc"]


# -- _should_flush_buffer ------------------------------------------


class TestShouldFlushBuffer:
    def test_empty_buffer_never_flushes(self):
        assert _should_flush_buffer("", 100) is False

    def test_buffer_at_chunk_size_flushes(self):
        assert _should_flush_buffer("x" * 200, 200) is True

    def test_buffer_below_chunk_size_no_flush(self):
        assert _should_flush_buffer("x" * 50, 200) is False

    def test_zero_chunk_size_always_flushes(self):
        assert _should_flush_buffer("x", 0) is True

    def test_negative_chunk_size_always_flushes(self):
        assert _should_flush_buffer("x", -1) is True


# -- parse_tool_call -----------------------------------------------


class TestParseToolCall:
    def test_valid_json(self):
        result = parse_tool_call('{"tool": "Read", "input": {"file_path": "/tmp/x"}}')
        assert result == ("Read", {"file_path": "/tmp/x"})

    def test_code_fence_json(self):
        text = '```json\n{"tool": "Glob", "input": {"pattern": "*.py"}}\n```'
        assert parse_tool_call(text) == ("Glob", {"pattern": "*.py"})

    def test_prose_returns_none(self):
        assert parse_tool_call("Hello, I'll help you with that.") is None

    def test_empty_returns_none(self):
        assert parse_tool_call("") is None
        assert parse_tool_call("   ") is None

    def test_missing_tool_key(self):
        assert parse_tool_call('{"input": {"x": 1}}') is None

    def test_missing_input_key(self):
        assert parse_tool_call('{"tool": "Read"}') is None

    def test_input_not_dict(self):
        assert parse_tool_call('{"tool": "Read", "input": "string"}') is None

    def test_json_array_returns_none(self):
        assert parse_tool_call('[1, 2, 3]') is None

    def test_tool_with_extra_fields_still_works(self):
        """Models sometimes add extra fields like "reasoning"."""
        result = parse_tool_call(
            '{"tool": "Read", "input": {"file_path": "/tmp/x"}, "reasoning": "need file"}'
        )
        assert result == ("Read", {"file_path": "/tmp/x"})


# -- execute_tool dispatch -----------------------------------------


class TestExecuteToolDispatch:
    def test_unknown_tool_returns_message(self):
        result = execute_tool("FakeWidget", {"x": 1})
        assert "Unknown tool" in result

    def test_read_missing_file_path(self):
        result = execute_tool("Read", {})
        assert "Missing" in result

    def test_write_missing_file_path(self):
        result = execute_tool("Write", {})
        assert "Missing" in result

    def test_edit_missing_params(self):
        result = execute_tool("Edit", {"file_path": "/tmp/x"})
        assert "Missing" in result

    def test_glob_missing_pattern(self):
        result = execute_tool("Glob", {})
        assert "Missing" in result

    def test_grep_missing_pattern(self):
        result = execute_tool("Grep", {})
        assert "Missing" in result

    def test_bash_missing_command(self):
        result = execute_tool("Bash", {})
        assert "Missing" in result

    def test_skill_missing_name(self):
        result = execute_tool("Skill", {})
        assert "Missing" in result


# -- _truncate ------------------------------------------------------


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello") == "hello"

    def test_long_text_truncated(self):
        long_text = "x" * 15000
        result = _truncate(long_text)
        assert len(result) < 15000
        assert result.endswith("[truncated]")

    def test_exact_limit_unchanged(self):
        text = "x" * _tools_mod.MAX_OUTPUT_CHARS
        assert _truncate(text) == text


# -- _resolve_path -------------------------------------------------


class TestResolvePath:
    def test_absolute_path_returned_as_is(self):
        result = _resolve_path("/tmp/test.txt")
        assert result == Path("/tmp/test.txt")

    def test_relative_path_resolved_to_base_dir(self):
        result = _resolve_path("README.md")
        assert result.is_absolute()
        assert str(result).endswith("README.md")

    def test_tilde_expanded(self):
        result = _resolve_path("~/test.txt")
        assert "~" not in str(result)


# -- _is_within -----------------------------------------------------


class TestIsWithin:
    def test_path_within_root(self):
        assert _is_within(Path("/tmp/x"), [Path("/tmp")]) is True

    def test_path_outside_all_roots(self):
        assert _is_within(Path("/etc/passwd"), [Path("/tmp"), Path("/home")]) is False

    def test_path_is_root_itself(self):
        assert _is_within(Path("/tmp"), [Path("/tmp")]) is True


# -- File operations with permissions -------------------------------


class TestFilePermissions:
    def test_read_outside_allowed_roots_blocked(self, monkeypatch):
        """Reading /etc/hostname should be blocked — it's outside all roots."""
        monkeypatch.setattr(config, "ADDITIONAL_DIRS", [])
        result = _read_file({"file_path": "/etc/hostname"})
        assert "blocked" in result.lower()

    def test_write_outside_allowed_roots_blocked(self, monkeypatch):
        """Writing to /etc should be blocked."""
        result = _write_file({"file_path": "/etc/evil.txt", "content": "evil"})
        assert "blocked" in result.lower()

    def test_read_nonexistent_file(self):
        result = _read_file({"file_path": "/tmp/nonexistent_xyz_12345.txt"})
        assert "not found" in result.lower()

    def test_read_within_base_dir_allowed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "BASE_DIR", tmp_path)
        f = tmp_path / "readable.txt"
        f.write_text("content here")
        result = _read_file({"file_path": str(f)})
        assert "content here" in result


# -- _bash_allowed edge cases ---------------------------------------


class TestBashAllowedEdgeCases:
    def test_empty_command(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(python:*)")
        assert _bash_allowed("") is False

    def test_command_with_semicolons_blocked(self, monkeypatch):
        """python; is not python — semicolons don't count as word boundary."""
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(python:*)")
        assert _bash_allowed("python; rm -rf /") is False

    def test_command_with_space_then_semicolons(self, monkeypatch):
        """python <space>; ... is allowed — space is a valid boundary."""
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(python:*)")
        assert _bash_allowed("python ; rm -rf /") is True

    def test_multiple_bash_patterns(self, monkeypatch):
        monkeypatch.setattr(
            config, "ALLOWED_TOOLS",
            "Bash(python:*),Bash(jq:*)"
        )
        assert _bash_allowed("python script.py") is True
        assert _bash_allowed("jq '.data' file.json") is True
        assert _bash_allowed("curl evil.com") is False

    def test_bare_bash_takes_precedence(self, monkeypatch):
        """Bare 'Bash' (no parens) allows everything, even with other patterns."""
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash,Bash(python:*)")
        assert _bash_allowed("rm -rf /") is True


# -- _run_bash execution -------------------------------------------


class TestRunBash:
    def test_blocked_command(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash(python:*)")
        result = _run_bash({"command": "rm -rf /"})
        assert "blocked" in result.lower()

    def test_successful_command(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash")
        result = _run_bash({"command": "echo hello"})
        assert "hello" in result

    def test_no_output_command(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOWED_TOOLS", "Bash")
        result = _run_bash({"command": "true"})
        assert "(no output)" in result


# -- _read_skill ----------------------------------------------------


class TestReadSkill:
    def test_existing_skill(self, monkeypatch, tmp_path):
        skill_dir = tmp_path / "skills" / "matomo_query"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Matomo Query Skill\nUse this...")
        monkeypatch.setattr(config, "BASE_DIR", tmp_path)

        result = _read_skill({"skill": "matomo_query"})
        assert "Matomo Query Skill" in result

    def test_missing_skill(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "BASE_DIR", tmp_path)
        result = _read_skill({"skill": "nonexistent_skill"})
        assert "not found" in result.lower()


# -- tool_protocol format ------------------------------------------


class TestToolProtocol:
    def test_contains_all_tools(self):
        proto = tool_protocol()
        for tool in ("Read", "Write", "Edit", "Glob", "Grep", "Bash", "Skill"):
            assert tool in proto

    def test_contains_json_examples(self):
        proto = tool_protocol()
        assert '"tool"' in proto
        assert '"input"' in proto

    def test_is_valid_instruction(self):
        proto = tool_protocol()
        # Should contain the "respond with JSON only" instruction
        assert "JSON" in proto


# -- _glob_files ----------------------------------------------------


class TestGlobFiles:
    def test_glob_finds_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "BASE_DIR", tmp_path)
        (tmp_path / "foo.py").write_text("x")
        (tmp_path / "bar.py").write_text("y")

        result = _glob_files({"pattern": "*.py"})
        assert "foo.py" in result
        assert "bar.py" in result

    def test_glob_no_matches(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "BASE_DIR", tmp_path)
        result = _glob_files({"pattern": "*.xyz_nonexistent"})
        assert "No matches" in result

    def test_glob_recursive(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "BASE_DIR", tmp_path)
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "deep.py").write_text("x")

        result = _glob_files({"pattern": "**/*.py"})
        assert "deep.py" in result


# -- llm.py backend routing ----------------------------------------


class TestLLMBackendRouting:
    def test_unsupported_backend_raises(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_BACKEND", "nonexistent")
        monkeypatch.setattr(config, "AGENT_BACKEND", "nonexistent")

        with pytest.raises(_llm_mod.LLMError, match="Unsupported"):
            _llm_mod.generate_text("hello")

    def test_ollama_backend_selected(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_BACKEND", "ollama")
        monkeypatch.setattr(config, "AGENT_BACKEND", "ollama")
        assert _llm_mod._get_llm_backend() == "ollama"

    def test_llm_backend_overrides_agent_backend(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_BACKEND", "sdk")
        monkeypatch.setattr(config, "AGENT_BACKEND", "ollama")
        assert _llm_mod._get_llm_backend() == "sdk"

    def test_llm_backend_defaults_to_agent_backend(self, monkeypatch):
        monkeypatch.setattr(config, "LLM_BACKEND", "")
        monkeypatch.setattr(config, "AGENT_BACKEND", "cli")
        assert _llm_mod._get_llm_backend() == "cli"


# -- _edit_file edge cases ------------------------------------------


class TestEditFileEdgeCases:
    def test_empty_old_string_matches_everywhere(self, tmp_path):
        """Empty string matches at every position in the file."""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = _edit_file({
            "file_path": str(f),
            "old_string": "",
            "new_string": "x",
        })
        # Empty string has count > 1 in any non-empty file
        assert "matches" in result

    def test_multiline_replace(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n")
        result = _edit_file({
            "file_path": str(f),
            "old_string": "line1\nline2",
            "new_string": "replaced",
        })
        assert "Edited" in result
        assert f.read_text() == "replaced\nline3\n"

    def test_replace_with_same_string(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world\n")
        result = _edit_file({
            "file_path": str(f),
            "old_string": "hello",
            "new_string": "hello",
        })
        # Should still "succeed" even if content doesn't change
        assert "Edited" in result


# -- _grep_files edge cases -----------------------------------------


class TestGrepFilesEdgeCases:
    def test_binary_file_skipped(self, tmp_path):
        """Binary files shouldn't crash grep."""
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\xff\xfe")
        result = _grep_files({"pattern": ".*", "path": str(f)})
        # Should handle gracefully — either match replacement chars or skip
        assert isinstance(result, str)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = _grep_files({"pattern": "anything", "path": str(f)})
        assert "No matches" in result

    def test_result_limit(self, tmp_path):
        """Grep caps at 200 results."""
        f = tmp_path / "many_matches.txt"
        f.write_text("\n".join(f"match_{i}" for i in range(300)))
        result = _grep_files({"pattern": "match_", "path": str(f)})
        lines = result.strip().split("\n")
        assert len(lines) <= 200
