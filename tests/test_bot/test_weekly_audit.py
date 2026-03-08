import datetime
import asyncio

from src.bot import main as bot_main


def test_weekly_audit_runs_on_sunday(monkeypatch):
    called = {}

    monkeypatch.setattr(datetime, "datetime", type("FakeDateTime", (), {
        "today": staticmethod(lambda: type("FakeDay", (), {"weekday": staticmethod(lambda: 6)})())
    }))
    monkeypatch.setattr(bot_main, "audit_predictions", lambda: called.setdefault("audit", True))

    asyncio.run(bot_main.weekly_audit.coro())
    assert called.get("audit") is True


def test_weekly_audit_skips_on_non_sunday(monkeypatch):
    called = {}

    monkeypatch.setattr(datetime, "datetime", type("FakeDateTime", (), {
        "today": staticmethod(lambda: type("FakeDay", (), {"weekday": staticmethod(lambda: 2)})())
    }))
    monkeypatch.setattr(bot_main, "audit_predictions", lambda: called.setdefault("audit", True))

    asyncio.run(bot_main.weekly_audit.coro())
    assert called.get("audit") is None