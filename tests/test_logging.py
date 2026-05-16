from patternloop.logging_setup import redact_text


def test_redact_ant_key() -> None:
    t = "token sk-ant-api03-XXXX secret"
    out = redact_text(t)
    assert "sk-ant-api" not in out
    assert "[REDACTED_ANT]" in out


def test_redact_bearer() -> None:
    t = "Authorization: Bearer abc.def.ghi"
    out = redact_text(t)
    assert "Bearer [REDACTED]" in out
