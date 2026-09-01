from app.models import mask_url, sha256_text
from app.signals import detect_signals
from app.verifier import verify


def test_mask_url():
    value = "https://example.com/report/2026"
    assert mask_url(value) == "examp" + ("•" * (len("example.com/report/2026") - 8)) + "026"


def test_no_protocol_in_masked_url():
    assert not mask_url("https://example.com/test").startswith("http")


def test_signal_detection_is_generic():
    signals = detect_signals("We are recruiting affiliates for a ransomware-as-a-service program")
    names = {item.name for item in signals}
    assert "affiliate_program" in names
    assert "ransomware_service" in names


def test_single_observation_is_not_verified():
    signals = detect_signals("ransomware-as-a-service affiliate program")
    result = verify(signals, independent_observations=1)
    assert result.status in {"candidate", "rejected"}
    assert result.confidence != "high"


def test_hash_is_stable():
    assert sha256_text("abc") == sha256_text("abc")
    assert len(sha256_text("abc")) == 64
