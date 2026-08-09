from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cinenode.api import create_app
from cinenode.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(home=tmp_path / "runtime", host="127.0.0.1", port=8787, max_upload_bytes=4 * 1024 * 1024, job_workers=1)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
