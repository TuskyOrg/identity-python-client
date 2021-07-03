import pytest

from tusky_users import _users


def test_bearer():
    t = _users.BearerToken(access_token="abc", token_type="bearer")
    assert dict(t) == {"access_token": "abc", "token_type": "bearer"}
    assert str(t) == '{"access_token": "abc", "token_type": "bearer"}'
