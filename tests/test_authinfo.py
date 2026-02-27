import subprocess

import ligonlibrary.authinfo as authinfo


def test_authinfo_prefers_authinfo_over_pass(monkeypatch):
    def fake_exists(path):
        return True

    def fake_check_output(args, stderr=None):
        if args[:2] == ["gpg", "--decrypt"]:
            return (
                b"machine api.openai.com login apikey password SECRET\n"
                b"machine api.github.com login ligon password GITHUB\n"
            )
        if args[:2] == ["pass", "show"]:
            raise AssertionError("pass should not be consulted when authinfo matches")
        raise AssertionError(f"unexpected call: {args}")

    monkeypatch.setattr(authinfo.os.path, "exists", fake_exists)
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    assert (
        authinfo.get_password_for_machine("api.openai.com", login="apikey") == "SECRET"
    )


def test_authinfo_falls_back_to_pass_when_missing(monkeypatch):
    def fake_exists(path):
        return True

    def fake_check_output(args, stderr=None):
        if args[:2] == ["gpg", "--decrypt"]:
            return b"machine other.com login user password OTHER\n"
        if args[:2] == ["pass", "ls"]:
            return (
                b"Password Store\n"
                b"\xe2\x94\x94\xe2\x94\x80\xe2\x94\x80 api.openai.com\n"
                b"    \xe2\x94\x94\xe2\x94\x80\xe2\x94\x80 apikey\n"
            )
        if args[:2] == ["pass", "show"]:
            assert args[2] == "api.openai.com/apikey"
            return b"PASSSECRET\nmetadata: ignored\n"
        raise AssertionError(f"unexpected call: {args}")

    monkeypatch.setattr(authinfo.os.path, "exists", fake_exists)
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    assert authinfo.get_password_for_machine("api.openai.com") == "PASSSECRET"


def test_pass_direct_login_lookup(monkeypatch):
    def fake_exists(path):
        return False

    def fake_check_output(args, stderr=None):
        if args[:2] == ["pass", "show"]:
            assert args[2] == "api.github.com/ligon"
            return b"GITHUBSECRET\n"
        raise AssertionError(f"unexpected call: {args}")

    monkeypatch.setattr(authinfo.os.path, "exists", fake_exists)
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    assert (
        authinfo.get_password_for_machine("api.github.com", login="ligon")
        == "GITHUBSECRET"
    )
