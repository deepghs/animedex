"""``animedex ghibli <subcommand>`` Click group + bindings."""

from __future__ import annotations

import click

from animedex.backends import ghibli as _api
from animedex.entry._cli_factory import register_subcommand


@click.group(name="ghibli")
def ghibli_group() -> None:
    """High-level Studio Ghibli commands (offline bundled snapshot).

    \b
    Docs:
      https://ghibliapi.vercel.app/                  live API reference
      https://github.com/janismdhanbad/studio-ghibli-api   source repository

    \b
    Examples:
      animedex ghibli films
      animedex ghibli films --director "Hayao Miyazaki" --min-rt-score 90
      animedex ghibli people Haku
      animedex ghibli vehicles
    \f

    Backend: Studio Ghibli API snapshot bundled with animedex
    (live source: ghibliapi.vercel.app).

    Rate limit: not applicable for high-level commands; all reads are
    served from the bundled offline snapshot.

    --- LLM Agent Guidance ---
    Offline, deterministic metadata lookup for Studio Ghibli films,
    people, locations, species, and vehicles. Use this high-level
    group by default because it does not touch the network. Use
    ``animedex api ghibli`` only when the user explicitly asks for
    live upstream data.
    --- End ---
    """


register_subcommand(ghibli_group, "films", _api.films, help="List films from the bundled snapshot.")
register_subcommand(ghibli_group, "film", _api.film, help="One film by Studio Ghibli API UUID.")
register_subcommand(ghibli_group, "people", _api.people, help="List people from the bundled snapshot.")
register_subcommand(ghibli_group, "person", _api.person, help="One person by Studio Ghibli API UUID.")
register_subcommand(ghibli_group, "locations", _api.locations, help="List locations from the bundled snapshot.")
register_subcommand(ghibli_group, "location", _api.location, help="One location by Studio Ghibli API UUID.")
register_subcommand(ghibli_group, "vehicles", _api.vehicles, help="List vehicles from the bundled snapshot.")
register_subcommand(ghibli_group, "vehicle", _api.vehicle, help="One vehicle by Studio Ghibli API UUID.")
register_subcommand(ghibli_group, "species", _api.species, help="List species from the bundled snapshot.")
register_subcommand(ghibli_group, "species-by-id", _api.species_by_id, help="One species by Studio Ghibli API UUID.")
