from tests.util import login
from crashserver.config import settings


class TestEmptyProject:
    def test_path_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"No projects have been created yet." in response.data

    def test_path_crash_reports(self, client):
        response = client.get("/crash-reports")
        assert response.status_code == 200
        assert b"No minidumps have been uploaded yet." in response.data

    def test_settings_unauthenticated(self, client):
        response = client.get("/settings")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_settings_authenticated(self, client):
        login(client, settings.login.email, settings.login.passwd)
        response = client.get("/settings", follow_redirects=True)
        assert response.status_code == 200
        assert b"Crash Server supports collecting symbols and minidumps for multiple applications" in response.data
