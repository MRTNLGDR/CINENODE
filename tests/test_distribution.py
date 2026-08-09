from pathlib import Path

from cinenode.verify import verify_distribution, verify_source


def test_distribution_contains_ui_and_modules():
    assert verify_distribution()["ok"] is True


def test_source_verifier():
    root=Path(__file__).resolve().parents[1]
    assert verify_source(root)["ok"] is True
