"""Top-level shim so ``python animedex_cli.py`` invokes the CLI."""

from animedex.entry import animedex_cli

if __name__ == "__main__":
    animedex_cli()
