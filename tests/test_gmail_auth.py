from unittest.mock import Mock

from cogs.flight_alerts import auth_gmail


def test_refreshed_token_remains_usable_when_token_file_is_read_only(
    monkeypatch,
):
    credentials = Mock(valid=False)
    service = object()
    monkeypatch.setattr(
        auth_gmail.Credentials,
        "from_authorized_user_file",
        Mock(return_value=credentials),
    )
    monkeypatch.setattr(auth_gmail, "Request", Mock(return_value=object()))
    monkeypatch.setattr(auth_gmail, "build", Mock(return_value=service))

    def deny_write(*args, **kwargs):
        raise PermissionError("read-only file system")

    monkeypatch.setattr("builtins.open", deny_write)

    assert auth_gmail.authenticate_gmail() is service
    credentials.refresh.assert_called_once()
    auth_gmail.build.assert_called_once_with("gmail", "v1", credentials=credentials)
