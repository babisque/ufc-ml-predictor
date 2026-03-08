import pandas as pd

from src.scraper import events


class DummyResponse:
    def __init__(self, html: str, status_code: int = 200):
        self.content = html.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")


def test_get_next_event(monkeypatch):
    html = """
    <table>
      <tr class="b-statistics__table-row">
        <td>
          <a class="b-link" href="http://event-link">UFC Future</a>
          <span class="b-statistics__date">Jan 01, 2030</span>
          <img src="next.png" />
        </td>
      </tr>
    </table>
    """

    monkeypatch.setattr(events.requests, "get", lambda *args, **kwargs: DummyResponse(html))
    result = events.get_next_event()
    assert result["name"] == "UFC Future"
    assert result["link"] == "http://event-link"
    assert result["date"] == "Jan 01, 2030"


def test_get_event_fights(monkeypatch):
    html = """
    <tbody class="b-fight-details__table-body">
      <tr>
        <td></td>
        <td><a class="b-link b-link_style_black">Fighter A</a><a class="b-link b-link_style_black">Fighter B</a></td>
        <td></td><td></td><td></td><td></td>
        <td>Lightweight Bout</td>
      </tr>
    </tbody>
    """
    monkeypatch.setattr(events.requests, "get", lambda *args, **kwargs: DummyResponse(html))
    fights = events.get_event_fights("http://event-link")
    assert fights == [("Fighter A", "Fighter B", "Lightweight")]


def test_get_all_events(monkeypatch):
    html = """
    <table>
      <tr class="b-statistics__table-row"><th>header</th></tr>
      <tr class="b-statistics__table-row">
        <td>
          <a href="http://e1">UFC 1</a>
          <span>Nov 12, 1993</span>
        </td>
        <td>Denver, Colorado</td>
      </tr>
    </table>
    """
    monkeypatch.setattr(events.requests, "get", lambda *args, **kwargs: DummyResponse(html))
    df = events.get_all_events()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert set(["name", "date", "location", "link"]).issubset(df.columns)