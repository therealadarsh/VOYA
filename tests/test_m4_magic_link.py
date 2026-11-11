from voya.accounts.magic_link import FakeMailer, MagicLinkService
from voya.store import Store


def test_magic_link_email_flow(monkeypatch):
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "0")
    st = Store(":memory:")
    mail = FakeMailer()
    svc = MagicLinkService(st, mail)
    out = svc.request_sign_in("tripper@example.com", True)
    assert out["status"] == "email_sent"
    assert not out.get("token")
    assert len(mail.sent) == 1
    _email, url = mail.sent[0]
    assert "tripper@example.com" in _email
    token = url.split("token=")[-1]
    verified = svc.verify(token)
    assert verified and verified.get("token")
