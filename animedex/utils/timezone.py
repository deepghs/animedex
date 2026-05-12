"""Timezone parsing helpers shared by aggregate commands and renderers.

The CLI accepts fixed offsets, IANA names, local time, and the broader
set of timezone strings supported by :mod:`dateutil.tz`. Keeping this
logic in one module avoids each command growing a slightly different
timezone parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil import tz as dateutil_tz

_OFFSET_RE = re.compile(r"^([+-])(\d{1,2})(?::?(\d{2}))?$")
_OFFSET_PREFIX_RE = re.compile(r"^(?:utc|gmt)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$", re.IGNORECASE)
_UTC_ALIASES = frozenset({"utc", "z", "gmt"})


@dataclass(frozen=True)
class TimezoneResolution:
    """Resolved timezone value and display label.

    :ivar tzinfo: Concrete timezone object used for datetime math.
    :vartype tzinfo: datetime.tzinfo
    :ivar label: Stable human-readable label carried into rendered
                 aggregate results.
    :vartype label: str
    """

    tzinfo: tzinfo
    label: str


def now_local() -> datetime:
    """Return the current local aware datetime.

    :return: Local aware datetime.
    :rtype: datetime.datetime
    """
    return datetime.now().astimezone()


def timezone_label(tz: tzinfo, *, sample: Optional[datetime] = None) -> str:
    """Return a stable display label for a timezone object.

    :param tz: Timezone object.
    :type tz: datetime.tzinfo
    :param sample: Optional datetime used for offset/name sampling.
    :type sample: datetime.datetime or None
    :return: IANA key, ``"UTC"``, fixed offset, or timezone name.
    :rtype: str
    """
    key = getattr(tz, "key", None)
    if isinstance(key, str) and key:
        return key
    if tz is timezone.utc:
        return "UTC"
    sample_dt = sample or now_local()
    offset = tz.utcoffset(sample_dt)
    if offset is not None:
        total_seconds = int(offset.total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        total_seconds = abs(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{sign}{hours:02d}:{minutes:02d}"
    name = tz.tzname(sample_dt)
    return name or "local"


def _fixed_offset(sign: str, hours_text: str, minutes_text: Optional[str]) -> Optional[TimezoneResolution]:
    hours = int(hours_text)
    minutes = int(minutes_text or "0")
    if hours > 23 or minutes > 59:
        return None
    delta = timedelta(hours=hours, minutes=minutes)
    if sign == "-":
        delta = -delta
    label = f"{sign}{hours:02d}:{minutes:02d}"
    return TimezoneResolution(timezone(delta, name=label), label)


def parse_timezone(value: Optional[str], *, local_now: Optional[datetime] = None) -> TimezoneResolution:
    """Parse a user-facing timezone string.

    Accepted forms include ``local``, ``UTC``/``Z``/``GMT``, IANA
    names such as ``Asia/Tokyo``, fixed offsets such as ``+08:00`` or
    ``+8``, prefixed offsets such as ``UTC+8`` or ``GMT-05:00``, and
    any additional timezone syntax understood by :func:`dateutil.tz.gettz`.

    :param value: User-provided timezone value. ``None`` means local.
    :type value: str or None
    :param local_now: Optional local datetime override for tests.
    :type local_now: datetime.datetime or None
    :return: Resolved timezone and display label.
    :rtype: TimezoneResolution
    :raises ValueError: If the value cannot be parsed.
    """
    raw = (value or "local").strip()
    if not raw or raw.lower() == "local":
        local = local_now or now_local()
        tz = local.tzinfo or timezone.utc
        return TimezoneResolution(tz, timezone_label(tz, sample=local))

    compact = re.sub(r"\s+", "", raw)
    if compact.lower() in _UTC_ALIASES:
        return TimezoneResolution(timezone.utc, "UTC")

    match = _OFFSET_RE.match(compact)
    if match is not None:
        resolved = _fixed_offset(match.group(1), match.group(2), match.group(3))
        if resolved is None:
            raise ValueError(f"unknown timezone: {value!r}")
        return resolved

    prefixed = _OFFSET_PREFIX_RE.match(compact)
    if prefixed is not None:
        resolved = _fixed_offset(prefixed.group(1), prefixed.group(2), prefixed.group(3))
        if resolved is None:
            raise ValueError(f"unknown timezone: {value!r}")
        return resolved

    try:
        return TimezoneResolution(ZoneInfo(raw), raw)
    except ZoneInfoNotFoundError:
        pass

    dateutil_tzinfo = dateutil_tz.gettz(raw)
    if dateutil_tzinfo is not None:
        return TimezoneResolution(dateutil_tzinfo, raw)

    raise ValueError(f"unknown timezone: {value!r}")


def selftest() -> bool:
    """Smoke-test broad timezone parsing.

    :return: ``True`` when local, IANA, fixed-offset, and dateutil TZ
             string parsing all work.
    :rtype: bool
    """
    assert parse_timezone("UTC").label == "UTC"
    assert parse_timezone("+8").label == "+08:00"
    assert parse_timezone("UTC+8").label == "+08:00"
    assert parse_timezone("Asia/Tokyo").label == "Asia/Tokyo"
    assert parse_timezone("CST-8").tzinfo.utcoffset(datetime(2026, 1, 1)).total_seconds() == 8 * 3600
    return True
