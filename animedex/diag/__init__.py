"""
Self-diagnostic helpers for animedex.

This sub-package contains routines that exercise the CLI from inside
its own process so that a built binary can verify itself in
environments where Python is not installed. The single public entry
point lives in :mod:`animedex.diag.selftest` as
:func:`animedex.diag.selftest.run_selftest`; import it from there
rather than re-exporting at this package level. CLI usage is
``animedex selftest``.
"""
