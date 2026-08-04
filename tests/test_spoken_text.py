"""A rich answer is displayed in full but SPOKEN as a concise lead-in.

Text-to-speech time scales with length, so reading a long comparison aloud was
the largest per-turn latency. `concise_spoken_text` keeps short answers intact
and, for long ones, speaks only the narrative lead plus a pointer to the on-screen
detail - never changing the displayed answer or any action.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.responses.spoken_text import SPOKEN_MAX_CHARS, concise_spoken_text

COMPARE = ("I found Samsung Galaxy S26, iPhone 17. Here is a source-backed comparison: "
           "- Samsung Galaxy S26: Brand: Samsung. Price: 74,699. Availability: In stock. "
           "- iPhone 17: Brand: Apple. Price: 79,900. Availability: In stock.")
SEARCH = ("I found 11 matching products: - Samsung Galaxy S26: Price 74699. "
          "- Samsung Galaxy S26 Ultra: Price 107899. - Samsung Galaxy S26+: Price 91299.")


def test_short_answers_are_spoken_verbatim():
    for text in ("I found 3 Samsung phones in stock.", "Hi, I am ready to help."):
        assert concise_spoken_text(text, []) == text


def test_a_long_comparison_is_shortened_to_a_lead_in():
    spoken = concise_spoken_text(COMPARE, [{"action": "SHOW_COMPARISON"}])
    assert len(spoken) < len(COMPARE), spoken
    assert len(spoken) <= SPOKEN_MAX_CHARS + len("The full details are on your screen.") + 2
    assert "on your screen" in spoken.lower()
    # The fact list (prices, brands) is NOT read aloud - it is on screen.
    assert "74,699" not in spoken and "79,900" not in spoken


def test_a_long_search_result_speaks_the_count_not_the_list():
    spoken = concise_spoken_text(SEARCH, [{"action": "SHOW_PRODUCTS"}])
    assert "11 matching products" in spoken
    assert "107899" not in spoken and "91299" not in spoken
    assert len(spoken) <= SPOKEN_MAX_CHARS + len("The full details are on your screen.") + 2


def test_the_lead_in_ends_on_a_clean_sentence():
    spoken = concise_spoken_text(COMPARE, [{"action": "SHOW_COMPARISON"}])
    lead = spoken.replace("The full details are on your screen.", "").strip()
    assert lead.endswith((".", "!", "?"))


def test_empty_input_is_safe():
    assert concise_spoken_text("", []) == ""
    assert concise_spoken_text(None, None) == ""
