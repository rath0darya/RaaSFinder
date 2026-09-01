from app.discovery.candidates import extract_candidates


def test_extracts_unique_public_urls():
    text = "See https://example.com/a and https://example.com/a. Ignore ftp://example.com."
    result = extract_candidates(text)

    assert [item.url for item in result] == ["https://example.com/a"]
    assert result[0].channel == "clearweb"


def test_preserves_channel():
    result = extract_candidates("https://example.org/report", channel="forum")

    assert result[0].channel == "forum"
