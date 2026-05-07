"""Allow ``python -m animedex`` to invoke the CLI.

The body is tested in production by the frozen-binary smoke test
(``make test_cli`` runs ``./dist/animedex --version`` etc., which
goes through this entry point inside the PyInstaller bundle), but
it is not reachable through pytest's in-process coverage tracer
because the ``__main__`` block only runs when this module is
executed as a script. Hence the ``pragma: no cover`` markers below.
"""

from animedex.entry import animedex_cli

if __name__ == "__main__":  # pragma: no cover - script entry point
    animedex_cli()  # pragma: no cover - script entry point
