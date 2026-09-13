from pathlib import Path

from harness.rollup import format_report, load_history, rollup_by_prompt_version


def test_load_history_reads_tsv_with_header(tmp_path: Path):
    path = tmp_path / "history.tsv"
    path.write_text(
        "timestamp\tprompt_version\tfixture\tmode\toutcome\tdomain_skill_match\tunits_pass\tunits_total\n"
        "2026-09-14T00:00:00Z\tabc123\tdept200-vb6\te2e\tsuccess\tTrue\t1\t1\n",
        encoding="utf-8",
    )

    rows = load_history(path)

    assert rows == [
        {
            "timestamp": "2026-09-14T00:00:00Z",
            "prompt_version": "abc123",
            "fixture": "dept200-vb6",
            "mode": "e2e",
            "outcome": "success",
            "domain_skill_match": "True",
            "units_pass": "1",
            "units_total": "1",
        }
    ]


def test_load_history_missing_file_returns_empty(tmp_path: Path):
    assert load_history(tmp_path / "missing.tsv") == []


def test_rollup_groups_by_prompt_version_and_computes_rates():
    rows = [
        {
            "prompt_version": "v1",
            "outcome": "success",
            "domain_skill_match": "True",
            "units_pass": "1",
            "units_total": "1",
        },
        {
            "prompt_version": "v1",
            "outcome": "needs-human",
            "domain_skill_match": "False",
            "units_pass": "0",
            "units_total": "1",
        },
        {
            "prompt_version": "v2",
            "outcome": "success",
            "domain_skill_match": "True",
            "units_pass": "2",
            "units_total": "2",
        },
    ]

    rollups = rollup_by_prompt_version(rows)

    by_version = {r["prompt_version"]: r for r in rollups}
    assert by_version["v1"]["runs"] == 2
    assert by_version["v1"]["success_rate"] == 0.5
    assert by_version["v1"]["domain_skill_match_rate"] == 0.5
    assert by_version["v1"]["units_pass_rate"] == 0.5
    assert by_version["v2"]["runs"] == 1
    assert by_version["v2"]["success_rate"] == 1.0
    assert by_version["v2"]["units_pass_rate"] == 1.0


def test_rollup_handles_no_expected_units_as_not_available():
    rows = [
        {
            "prompt_version": "v1",
            "outcome": "success",
            "domain_skill_match": "True",
            "units_pass": "0",
            "units_total": "0",
        }
    ]

    rollups = rollup_by_prompt_version(rows)

    assert rollups[0]["units_pass_rate"] is None


def test_format_report_renders_tsv_with_na_for_missing_units_pass_rate():
    rollups = [
        {
            "prompt_version": "v1",
            "runs": 2,
            "success_rate": 0.5,
            "domain_skill_match_rate": 0.5,
            "units_pass_rate": None,
        }
    ]

    report = format_report(rollups)

    assert report.splitlines()[0] == "prompt_version\truns\tsuccess_rate\tdomain_skill_match_rate\tunits_pass_rate"
    assert "v1\t2\t0.50\t0.50\tn/a" in report
