"""Shared test setup: tests never use the real API keys in .env (no real AI calls, no charges).
A test that needs a key sets a fake one itself."""
import pytest

import config


@pytest.fixture(autouse=True)
def no_real_ai_keys(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
