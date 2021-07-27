import warnings

import pytest

from tusky_users import _users

warnings.warn("THIS IS NOT A COMPREHENSIVE TEST SUITE, to say the least")


def test_bearer():
    t = _users.LoginResponse(access_token="abc", token_type="bearer")
    assert dict(t) == {"access_token": "abc", "token_type": "bearer"}
    assert str(t) == '{"access_token": "abc", "token_type": "bearer"}'
    with pytest.raises(NotImplementedError):
        for _ in t:
            pass
