from app.discovery.parser import parse_html


def test_parse_html_removes_script_and_extracts_title():
    html = """
    <html><head><title>Public report</title></head>
    <body><h1>Ransomware report</h1><script>secret = 1</script>
    <a href='https://example.com/x'>https://example.com/x</a></body></html>
    """
    page = parse_html(html, channel="clearweb")

    assert page.title == "Public report"
    assert "secret = 1" not in page.text
    assert page.links[0].url == "https://example.com/x"
