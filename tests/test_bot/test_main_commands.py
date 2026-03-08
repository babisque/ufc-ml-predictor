import asyncio

from src.bot import main as bot_main


class FakeMessage:
    def __init__(self, content=None):
        self.content = content
        self.edits = []

    async def edit(self, content=None, embed=None):
        self.edits.append({"content": content, "embed": embed})


class FakeCtx:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, embed=None):
        message = FakeMessage(content=content)
        self.sent.append({"content": content, "embed": embed, "message": message})
        return message


class DummyModel:
    def predict(self, X):
        return [1]

    def predict_proba(self, X):
        return [[0.1, 0.9]]


def test_predict_fight_rejects_invalid_format():
    ctx = FakeCtx()
    asyncio.run(bot_main.predict_fight.callback(ctx, args="Conor,Dustin"))

    assert len(ctx.sent) == 1
    assert "Invalid format" in ctx.sent[0]["content"]


def test_predict_fight_handles_missing_profiles(monkeypatch):
    ctx = FakeCtx()

    monkeypatch.setattr(bot_main, "get_fighter_profile", lambda *args, **kwargs: None)

    asyncio.run(bot_main.predict_fight.callback(ctx, args="Conor McGregor, Dustin Poirier, Lightweight"))

    status_message = ctx.sent[0]["message"]
    assert status_message.edits
    assert "Could not find profiles" in status_message.edits[-1]["content"]


def test_predict_fight_success_saves_prediction_and_returns_embed(monkeypatch):
    ctx = FakeCtx()
    saved = []

    fake_profile = {
        "name": "Conor McGregor",
        "age": 30,
        "height": 175,
        "reach": 188,
        "ctrl_hist_avg": 10,
        "sig_pct_hist_avg": 0.5,
        "kd_hist_avg": 0.2,
        "sig_str_landed_hist_avg": 3.0,
        "td_landed_hist_avg": 0.5,
    }

    monkeypatch.setattr(bot_main, "get_fighter_profile", lambda *args, **kwargs: fake_profile)
    monkeypatch.setattr(bot_main, "prepare_data_prevision", lambda *args, **kwargs: [[1, 2, 3]])
    monkeypatch.setattr(bot_main, "model", DummyModel())
    monkeypatch.setattr(bot_main, "save_prediction", lambda *args: saved.append(args))

    asyncio.run(bot_main.predict_fight.callback(ctx, args="Conor McGregor, Dustin Poirier, Lightweight"))

    assert len(saved) == 1
    assert saved[0][0] == "Individual fight"
    status_message = ctx.sent[0]["message"]
    assert status_message.edits[-1]["embed"] is not None


def test_next_event_handles_no_future_event(monkeypatch):
    ctx = FakeCtx()
    monkeypatch.setattr(bot_main, "get_next_event", lambda: None)

    asyncio.run(bot_main.next_event.callback(ctx))

    status_message = ctx.sent[0]["message"]
    assert status_message.edits[-1]["content"] == "No future events found."


def test_next_event_uses_cache(monkeypatch):
    ctx = FakeCtx()
    captured = {}

    async def fake_send_event_embeds(ctx_arg, status_message, event_name, event_date, fields, from_cache=False):
        captured["event_name"] = event_name
        captured["event_date"] = event_date
        captured["fields"] = fields
        captured["from_cache"] = from_cache

    monkeypatch.setattr(bot_main, "get_next_event", lambda: {"name": "UFC X", "link": "http://x", "date": "Jan 01, 2030"})
    monkeypatch.setattr(
        bot_main,
        "get_event_predictions",
        lambda event_name: [("A", "B", "LW", "A", 0.77)],
    )
    monkeypatch.setattr(bot_main, "_send_event_embeds", fake_send_event_embeds)

    asyncio.run(bot_main.next_event.callback(ctx))

    assert captured["event_name"] == "UFC X"
    assert captured["from_cache"] is True
    assert len(captured["fields"]) == 1


def test_show_stats_with_no_resolved_fights(monkeypatch):
    ctx = FakeCtx()
    monkeypatch.setattr(bot_main, "get_statistics", lambda: (0, 0, 3))

    asyncio.run(bot_main.show_stats.callback(ctx))

    assert "don't have enough" in ctx.sent[0]["content"]


def test_last_event_with_no_predictions(monkeypatch):
    ctx = FakeCtx()
    monkeypatch.setattr(bot_main, "get_last_event_predictions", lambda: (None, 0, 0, []))

    asyncio.run(bot_main.last_event.callback(ctx))

    assert ctx.sent[0]["content"] == "No predictions found for the last event."


def test_fighter_profile_not_found(monkeypatch):
    ctx = FakeCtx()
    monkeypatch.setattr(bot_main, "get_fighter_profile", lambda *args, **kwargs: None)

    asyncio.run(bot_main.fighter_profile.callback(ctx, fighter_name="unknown fighter"))

    assert "Could not find a profile" in ctx.sent[0]["content"]


def test_fighter_profile_success(monkeypatch):
    ctx = FakeCtx()
    profile = {
        "name": "Alex Pereira",
        "age": 36,
        "height": 193,
        "reach": 201,
        "ctrl_hist_avg": 95,
        "sig_pct_hist_avg": 0.58,
        "sig_str_landed_hist_avg": 4.5,
        "kd_hist_avg": 0.3,
        "td_landed_hist_avg": 0.2,
    }

    monkeypatch.setattr(bot_main, "get_fighter_profile", lambda *args, **kwargs: profile)

    asyncio.run(bot_main.fighter_profile.callback(ctx, fighter_name="alex pereira"))

    assert ctx.sent[0]["embed"] is not None
    assert "Alex Pereira" in ctx.sent[0]["embed"].title