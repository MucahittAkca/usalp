"""Agent main module helpers."""

from __future__ import annotations

import logging

import main as agent_main


def test_log_level_from_env_uses_named_level(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")

    assert agent_main._log_level_from_env() == logging.DEBUG


def test_log_level_from_env_uses_numeric_level(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "20")

    assert agent_main._log_level_from_env() == logging.INFO


def test_log_level_from_env_falls_back_for_unknown_value(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "not-a-level")

    assert agent_main._log_level_from_env() == logging.INFO
