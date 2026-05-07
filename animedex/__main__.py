"""Allow ``python -m animedex`` to invoke the CLI."""

from animedex.entry import animedex_cli

if __name__ == "__main__":
    animedex_cli()
