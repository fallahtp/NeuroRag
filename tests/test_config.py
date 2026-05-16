"""Tests for the central configuration module."""

import config


def test_env_int_returns_override(monkeypatch):
    monkeypatch.setenv("NEURORAG_TEST_INT", "42")
    assert config._env_int("NEURORAG_TEST_INT", 7) == 42


def test_env_int_returns_default_when_unset():
    assert config._env_int("NEURORAG_DEFINITELY_UNSET_KEY", 7) == 7


def test_env_int_returns_default_when_invalid(monkeypatch):
    monkeypatch.setenv("NEURORAG_TEST_BAD_INT", "not-a-number")
    assert config._env_int("NEURORAG_TEST_BAD_INT", 7) == 7


def test_env_str_returns_override(monkeypatch):
    monkeypatch.setenv("NEURORAG_TEST_STR", "custom")
    assert config._env_str("NEURORAG_TEST_STR", "default") == "custom"


def test_settings_has_expected_defaults():
    s = config.settings
    assert s.chunk_size == 1000
    assert s.chunk_overlap == 200
    assert s.top_k_fetch == 12
    assert s.top_k_final == 6
    assert s.max_chunks_per_paper == 2
    assert s.rrf_k == 60
    assert s.v1_ollama_model == "phi3:mini"
    assert s.v2_ollama_model == "qwen2.5:7b-instruct"
    assert s.grobid_url == "http://localhost:8070"


def test_settings_paths_are_under_base_dir():
    s = config.settings
    assert s.v1_index_dir.is_relative_to(s.base_dir)
    assert s.v2_index_dir.is_relative_to(s.base_dir)
    assert s.raw_dir.is_relative_to(s.data_dir)
