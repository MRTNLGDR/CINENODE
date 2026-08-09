from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from cinenode.api.app import create_app
from cinenode.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(home=tmp_path / "runtime", test_mode=True)


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as value:
        yield value
