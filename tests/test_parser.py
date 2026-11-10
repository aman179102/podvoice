"""Tests for podvoice Markdown script parsing (no model or audio needed)."""

from podvoice.parser import parse_markdown_script


def test_whitespace_only_emotion_normalises_to_none():
    segments = parse_markdown_script("[Bob | ]\nHello there.\n", source="t.md")
    assert len(segments) == 1
    assert segments[0].speaker == "Bob"
    assert segments[0].emotion is None
    assert segments[0].text == "Hello there."


def test_real_emotion_is_kept():
    segments = parse_markdown_script("[Bob | excited]\nHello there.\n", source="t.md")
    assert segments[0].emotion == "excited"


def test_missing_emotion_is_none():
    segments = parse_markdown_script("[Bob]\nHello there.\n", source="t.md")
    assert segments[0].emotion is None
