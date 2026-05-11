"""Cross-source aggregate commands.

The aggregate package composes existing high-level backend helpers.
It owns prefix-encoded entity references, type-to-backend routing,
and generic fan-out handling for partial source failures.
"""

from animedex.agg._fanout import FanoutSource, run_fanout
from animedex.agg.search import search
from animedex.agg.show import show

__all__ = ["FanoutSource", "run_fanout", "search", "show"]


def selftest() -> bool:
    """Smoke-test the aggregate package exports.

    :return: ``True`` on success.
    :rtype: bool
    """
    assert callable(run_fanout)
    assert callable(search)
    assert callable(show)
    return True
