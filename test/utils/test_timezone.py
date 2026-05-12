"""Tests for :mod:`animedex.utils.timezone`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

import pytest

pytestmark = pytest.mark.unittest


class NamedOnlyTimezone(tzinfo):
    def utcoffset(self, dt):
        return None

    def tzname(self, dt):
        return "named-only"

    def dst(self, dt):
        return None


def test_parse_timezone_accepts_flexible_user_inputs():
    from animedex.utils.timezone import parse_timezone

    assert parse_timezone("UTC").label == "UTC"
    assert parse_timezone("Z").label == "UTC"
    assert parse_timezone("+8").label == "+08:00"
    assert parse_timezone("-0230").label == "-02:30"
    assert parse_timezone("UTC+8").label == "+08:00"
    assert parse_timezone("GMT-05:00").label == "-05:00"
    assert parse_timezone("Asia/Tokyo").label == "Asia/Tokyo"
    assert parse_timezone("CST-8").tzinfo.utcoffset(datetime(2026, 1, 1)).total_seconds() == 8 * 3600


def test_parse_timezone_handles_local_and_errors():
    from animedex.utils.timezone import parse_timezone

    local_tz = timezone(timedelta(hours=-5), name="fixed-local")
    resolved = parse_timezone(None, local_now=datetime(2026, 5, 11, tzinfo=local_tz))

    assert resolved.label == "-05:00"
    with pytest.raises(ValueError):
        parse_timezone("+24:00")
    with pytest.raises(ValueError):
        parse_timezone("No/Such_Zone")


def test_timezone_label_falls_back_to_name():
    from animedex.utils.timezone import timezone_label

    assert timezone_label(timezone(timedelta(hours=2), name="custom")) == "+02:00"
    assert timezone_label(NamedOnlyTimezone()) == "named-only"


def test_selftest_runs():
    from animedex.utils import timezone

    assert timezone.selftest() is True
