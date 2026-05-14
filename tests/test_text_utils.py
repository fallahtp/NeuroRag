"""Tests for the pure text-processing helpers used across the pipelines."""

from chat_structured_ollama import (
    clean_text,
    split_into_sentences,
    strip_prefixed_metadata,
    tokenize,
)
from load_documents import resolve_text_path
from run_grobid_dual import looks_like_xml


def test_clean_text_collapses_whitespace():
    assert clean_text("hello   \n\t  world") == "hello world"


def test_clean_text_strips_null_bytes():
    assert "\x00" not in clean_text("a\x00b")


def test_tokenize_lowercases_and_drops_short_tokens():
    tokens = tokenize("HCN channels in SGN ab")
    assert "hcn" in tokens
    assert "channels" in tokens
    assert "ab" not in tokens  # shorter than the 3-char minimum


def test_strip_prefixed_metadata_removes_enrichment_prefix():
    text = (
        "Title: Foo\n"
        "Year: 2020\n"
        "Section title: Methods\n"
        "\n"
        "Real body content here."
    )
    assert strip_prefixed_metadata(text) == "Real body content here."


def test_strip_prefixed_metadata_keeps_unprefixed_body():
    assert strip_prefixed_metadata("Just body text.") == "Just body text."


def test_split_into_sentences():
    assert split_into_sentences("First sentence. Second one! Third?") == [
        "First sentence.",
        "Second one!",
        "Third?",
    ]


def test_split_into_sentences_empty_input():
    assert split_into_sentences("   ") == []


def test_looks_like_xml_accepts_tei_and_xml_declarations():
    assert looks_like_xml('<?xml version="1.0"?><TEI>')
    assert looks_like_xml('﻿<TEI xmlns="http://www.tei-c.org/ns/1.0">')
    assert looks_like_xml("<tei:TEI>")


def test_looks_like_xml_rejects_non_tei_payloads():
    assert not looks_like_xml("<html><body>error</body></html>")
    assert not looks_like_xml("plain text response")
    assert not looks_like_xml("")


def test_resolve_text_path_strips_data_raw_prefix():
    p = resolve_text_path("data/raw/ion_channels/paper.pdf")
    assert p.name == "paper.txt"
    assert "processed" in p.parts
    assert "ion_channels" in p.parts
    assert "raw" not in p.parts
