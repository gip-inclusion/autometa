import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_test_quality", Path(__file__).parent.parent / "scripts" / "check_test_quality.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
check_source = _module.check_source
check_dod_budget = _module.check_dod_budget
main = _module.main
iter_test_files = _module._iter_test_files
MAX_DOD_CRITERIA = _module.MAX_DOD_CRITERIA


def messages(source):
    return [reason for _, reason in check_source(source)]


@pytest.mark.parametrize(
    "source",
    [
        "def test_nothing():\n    result = compute()\n",
        "def test_nothing():\n    obj.do_it()\n",
        "async def test_nothing():\n    await obj.do_it()\n",
    ],
)
def test_flags_test_without_verification(source):
    msgs = messages(source)
    assert len(msgs) == 1
    assert "sans vérification" in msgs[0]


@pytest.mark.parametrize(
    "source",
    [
        "def test_ok():\n    assert compute() == 3\n",
        "def test_ok():\n    with pytest.raises(ValueError):\n        boom()\n",
        "def test_ok():\n    mock.assert_called_once_with(1)\n",
        "def test_ok():\n    obj.assertEqual(a, b)\n",
        "def test_ok():\n    pytest.fail('nope')\n",
        "def test_ok():\n    expect(page).to_have_url('/x')\n",
    ],
)
def test_accepts_real_verification(source):
    assert messages(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "@pytest.mark.skip\ndef test_skipped():\n    result = compute()\n",
        "@skip\ndef test_skipped():\n    result = compute()\n",
        "def test_skipped():\n    pytest.skip('later')\n",
    ],
)
def test_exempts_skipped_tests(source):
    assert messages(source) == []


def test_ignores_non_test_functions():
    assert messages("def helper():\n    x = compute()\n") == []


@pytest.mark.parametrize(
    "source",
    [
        "def test_taut():\n    assert True\n",
        "def test_taut():\n    assert 1\n",
    ],
)
def test_flags_constant_truthy_assertion(source):
    msgs = messages(source)
    assert len(msgs) == 1
    assert "tautologique" in msgs[0]


@pytest.mark.parametrize(
    "source",
    [
        "def test_x():\n    assert 'x'\n",
        "def test_x():\n    assert value == value\n",
        "def test_x():\n    assert value is value\n",
    ],
)
def test_leaves_ruff_covered_tautologies_to_ruff(source):
    assert messages(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "def test_real():\n    assert value == 3\n",
        "def test_real():\n    assert left == right\n",
        "def test_real():\n    assert obj.a == obj.b\n",
        "def test_real():\n    assert value < 3\n",
    ],
)
def test_accepts_meaningful_assertion(source):
    assert messages(source) == []


def test_iter_test_files_walks_dirs_and_filters_explicit_paths(tmp_path):
    (tmp_path / "test_a.py").write_text("")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "test_b.py").write_text("")
    (tmp_path / "helper.py").write_text("")

    walked = sorted(p.name for p in iter_test_files([str(tmp_path)]))
    assert walked == ["test_a.py", "test_b.py"]

    explicit = list(iter_test_files([str(tmp_path / "test_a.py")]))
    assert [p.name for p in explicit] == ["test_a.py"]

    assert list(iter_test_files([str(tmp_path / "helper.py")])) == []


def test_main_returns_zero_when_tests_are_clean(tmp_path, capsys):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert compute() == 3\n")
    exit_code = main([str(tmp_path)])
    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_main_reports_hollow_test_and_returns_one(tmp_path, capsys):
    (tmp_path / "test_bad.py").write_text("def test_bad():\n    compute()\n")

    exit_code = main([str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "test_bad.py" in out
    assert "sans vérification" in out


def dod_module(count):
    return "".join(f"def test_dod_{n}():\n    assert compute() == {n}\n\n" for n in range(1, count + 1))


@pytest.mark.parametrize("count", [0, 1, MAX_DOD_CRITERIA])
def test_dod_budget_accepts_up_to_the_bound(count):
    assert check_dod_budget(dod_module(count)) == []


def test_dod_budget_flags_every_criterion_beyond_the_bound():
    violations = check_dod_budget(dod_module(MAX_DOD_CRITERIA + 2))

    assert len(violations) == 2
    assert all("parcours de navigateur" in reason for _, reason in violations)


def test_dod_budget_only_applies_to_browser_tests(tmp_path, capsys):
    (tmp_path / "test_dods.py").write_text(dod_module(MAX_DOD_CRITERIA + 1))

    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""
