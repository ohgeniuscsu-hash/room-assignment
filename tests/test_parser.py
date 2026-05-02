import pytest
from src.parser import parse_period, is_unscheduled

class TestParsePeriod:
    def test_tilde_separator(self):
        assert parse_period("4~6") == {4, 5, 6}

    def test_dash_separator(self):
        assert parse_period("4-6") == {4, 5, 6}

    def test_single_period(self):
        assert parse_period("3~3") == {3}

    def test_overlap_detection(self):
        # 대학원 4~6 vs 학부 6~8 → 6 겹침
        grad = parse_period("4~6")
        undergrad = parse_period("6~8")
        assert grad & undergrad == {6}

    def test_no_overlap(self):
        grad = parse_period("4~5")
        undergrad = parse_period("6~8")
        assert grad & undergrad == set()

    def test_whitespace_ignored(self):
        assert parse_period(" 4 ~ 6 ") == {4, 5, 6}


class TestIsUnscheduled:
    def test_asterisk_prefix(self):
        assert is_unscheduled("*월 4~6") is True

    def test_zero_zero_pattern(self):
        assert is_unscheduled("0-0") is True

    def test_normal_period(self):
        assert is_unscheduled("4~6") is False

    def test_empty_string(self):
        assert is_unscheduled("") is True

    def test_none(self):
        assert is_unscheduled(None) is True
