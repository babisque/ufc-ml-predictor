import pytest

from src.ml import pipeline


def test_execute_complete_pipeline_runs_expected_scripts_in_order(monkeypatch):
    executed = []

    def fake_run_script(path):
        executed.append(path)

    monkeypatch.setattr(pipeline, "run_script", fake_run_script)

    pipeline.execute_complete_pipeline()

    assert executed == [
        "src/scraper/events.py",
        "src/scraper/fights.py",
        "src/scraper/fighters.py",
        "src/scraper/details.py",
        "src/processing/clean_data.py",
        "src/processing/clean_fighters.py",
        "src/processing/merge_data.py",
        "src/processing/shuffle_data.py",
        "train.py",
    ]


def test_run_script_exits_on_nonzero_returncode(monkeypatch):
    class Result:
        returncode = 1

    monkeypatch.setattr(pipeline.subprocess, "run", lambda *args, **kwargs: Result())

    with pytest.raises(SystemExit):
        pipeline.run_script("dummy.py")