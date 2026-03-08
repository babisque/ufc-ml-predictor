from bs4 import BeautifulSoup

from src.scraper.details import extract_header_stats, extract_values
from src.scraper.fighters import clean_text


def test_clean_text_fighters():
    assert clean_text(" A \n B ") == "A   B"


def test_extract_values():
    soup = BeautifulSoup("<td><p>10 of 20</p><p>5 of 10</p></td>", "html.parser")
    td = soup.find("td")
    f1, f2 = extract_values(td)
    assert f1 == "10 of 20"
    assert f2 == "5 of 10"


def test_extract_header_stats():
    html = """
    <div class="b-fight-details__content">
      <i class="b-fight-details__text-item"><i class="b-fight-details__label">Round:</i> 3</i>
      <i class="b-fight-details__text-item"><i class="b-fight-details__label">Time:</i> 4:31</i>
      <i class="b-fight-details__text-item"><i class="b-fight-details__label">Time format:</i> 3 Rnd (5-5-5)</i>
      <i class="b-fight-details__text-item"><i class="b-fight-details__label">Referee:</i> Herb Dean</i>
      <p class="b-fight-details__text">Method: SUB</p>
      <p class="b-fight-details__text">Details: Rear Naked Choke</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    stats = extract_header_stats(soup)
    assert stats["total_rounds"] == "3"
    assert stats["last_round_time"] == "4:31"
    assert stats["time_format"] == "3 Rnd (5-5-5)"
    assert stats["referee"] == "Herb Dean"
    assert stats["win_method_details"] == "Rear Naked Choke"