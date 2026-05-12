"""Aggregate orchestration helpers and top-level multi-source APIs.

The package owns backend fan-out and aggregate-specific coordination.
Backend adapters remain under :mod:`animedex.backends`; aggregate
modules compose those public Python APIs without reimplementing their
wire logic.
"""

from animedex.agg.calendar import schedule, season
from animedex.agg._fanout import FanoutSource, run_fanout
from animedex.agg.search import search
from animedex.agg.show import show

__all__ = ["FanoutSource", "run_fanout", "schedule", "search", "season", "show"]


def selftest() -> bool:
    """Smoke-test the aggregate package exports.

    :return: ``True`` when the package-level public names are wired.
    :rtype: bool
    """
    assert callable(season)
    assert callable(schedule)
    assert callable(search)
    assert callable(show)
    assert callable(run_fanout)
    return True
