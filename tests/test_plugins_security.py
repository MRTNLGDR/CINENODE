from pathlib import Path
import pytest

from cinenode.config import Settings
from cinenode.engines.http_adapters import MockEngine
from cinenode.engines.registry import EngineRegistry
from cinenode.plugins.loader import load_plugins


def test_registry_is_instance_scoped():
    one=EngineRegistry(); two=EngineRegistry(); one.register(MockEngine()); assert one.list(); assert two.list()==[]


def test_plugins_require_allowlist(tmp_path: Path):
    directory=tmp_path/"plugins"; directory.mkdir(); (directory/"demo.py").write_text("from cinenode.plugins.sdk import Plugin\ndef create_plugin(): return Plugin(id='demo',version='1')\n")
    assert load_plugins(directory,set())==[]; assert load_plugins(directory,{"demo"})[0].id=="demo"


def test_server_mode_requires_token(tmp_path: Path):
    with pytest.raises(ValueError): Settings(home=tmp_path,host="0.0.0.0",mode="server",auth_token="short").prepare()
