"""Tests for PDF filename metadata parsing."""

import pytest

from create_metadata import parse_filename_metadata


@pytest.mark.parametrize(
    "stem,expected",
    [
        ("2020_Smith_HCN_channels", ("2020", "Smith")),
        ("Smith_2020_HCN_channels", ("2020", "Smith")),
        ("1999_Jones_review", ("1999", "Jones")),
        ("Doe_et_al_2021_modeling", ("2021", "Doe")),
        ("no_year_in_this_name", ("", "no")),
        ("2018", ("2018", "")),
        ("", ("", "")),
    ],
)
def test_parse_filename_metadata(stem, expected):
    assert parse_filename_metadata(stem) == expected


def test_year_found_regardless_of_position():
    """A year must be extracted whether it leads or trails the filename."""
    year_first, _ = parse_filename_metadata("2015_paper")
    year_last, _ = parse_filename_metadata("paper_2015")
    assert year_first == year_last == "2015"


def test_non_year_digits_are_not_treated_as_year():
    """A 4-digit number outside the 19xx/20xx range is not a year."""
    year, _ = parse_filename_metadata("dataset_1234_v2")
    assert year == ""
