from tests.util import login, logout
from crashserver.config import settings


class TestLogin:
    def test_user_login(self, client):
        res = login(client, settings.login.email, settings.login.passwd)
        assert b"Logged in" in res.data

    def test_user_logout(self, client):
        login(client, settings.login.email, settings.login.passwd)
        res = logout(client)
        assert b"Logged out" in res.data

    def test_user_login_bad_user(self, client):
        res = login(client, f"{settings.login.email}x", settings.login.passwd)
        assert b"Invalid email or password" in res.data

    def test_user_login_bad_pass(self, client):
        res = login(client, settings.login.email, f"{settings.login.passwd}x")
        assert b"Invalid email or password" in res.data
