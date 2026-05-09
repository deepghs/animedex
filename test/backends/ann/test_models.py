"""Tests for ANN rich model helpers."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from animedex.models.common import SourceTag


pytestmark = pytest.mark.unittest


def _src() -> SourceTag:
    return SourceTag(backend="ann", fetched_at=datetime(2026, 5, 9, tzinfo=timezone.utc))


class TestCommonProjection:
    def test_anime_from_xml_node_projects_long_tail_fields(self):
        from animedex.backends.ann.models import AnnXmlNode, anime_from_node
        from animedex.render.xml import xml_text_to_dict

        raw = AnnXmlNode.from_adapter(
            xml_text_to_dict(
                """
                <anime id="1" gid="g1" type="TV" name="Sample" precision="TV" generated-on="2026-05-09T00:00:00Z">
                  <related-prev rel="prequel" id="0" />
                  <related-next rel="sequel" id="2" />
                  <info type="Picture" src="https://img.example/cover.jpg" />
                  <info type="Main title" lang="EN">Sample Main</info>
                  <info type="Alternative title" lang="JA">Sample Native</info>
                  <info type="Genres">adventure</info>
                  <info type="Themes">magic</info>
                  <info type="Number of episodes">12</info>
                  <info type="Vintage">2023-09-29 to 2023-12-15</info>
                  <info type="Plot Summary">A fixture-sized plot.</info>
                  <info type="Objectionable content">Mild</info>
                  <staff><task>Director</task><person id="10">Director Name</person></staff>
                  <staff><task>Writer</task></staff>
                  <cast lang="JA"><role>Hero</role><person id="20">Actor Name</person></cast>
                  <cast><role>Villain</role></cast>
                  <credit><task>Animation Production</task><company id="30">Studio Name</company></credit>
                  <credit><task>Distribution</task></credit>
                  <episode num="1"><title type="Main title">Episode One</title></episode>
                  <review href="https://example.test/review">Review</review>
                  <release href="https://example.test/release">Release</release>
                  <news href="https://example.test/news">News</news>
                </anime>
                """
            )
        )

        anime = anime_from_node(raw, _src())
        common = anime.to_common()

        assert anime.id == "1"
        assert [row.direction for row in anime.relations] == ["prev", "next"]
        assert anime.staff[0].to_common().occupations == ["Director"]
        assert anime.staff[1].to_common().name == ""
        assert anime.cast[0].to_common().role == "JA"
        assert anime.cast[1].to_common().name == "Villain"
        assert anime.episodes[0].titles[0].text == "Episode One"
        assert anime.reviews[0].text == "Review"
        assert anime.releases[0].text == "Release"
        assert anime.news[0].text == "News"
        assert common.id == "ann:1"
        assert common.title.romaji == "Sample Main"
        assert common.title.native == "Sample Native"
        assert common.episodes == 12
        assert common.studios == ["Studio Name"]
        assert common.description == "A fixture-sized plot."
        assert common.genres == ["adventure"]
        assert common.tags == ["magic"]
        assert common.format == "TV"
        assert common.aired_from == date(2023, 9, 29)
        assert common.cover_image_url == "https://img.example/cover.jpg"
        assert common.age_rating == "Mild"
        assert common.ids == {"ann": "1"}

    def test_direct_refs_use_fallback_source_when_needed(self):
        from animedex.backends.ann.models import AnnCast, AnnPersonRef, AnnStaff

        staff = AnnPersonRef(id="42", name="Person Name").to_common_staff(None, ["Layout"])
        empty_staff = AnnStaff().to_common()
        cast = AnnCast(attrs={"lang": "EN"}, role="Narrator").to_common()

        assert staff.id == "ann:person:42"
        assert staff.source.backend == "ann"
        assert empty_staff.id == "ann:person:unknown"
        assert empty_staff.source.backend == "ann"
        assert cast.id == "ann:character:Narrator"
        assert cast.role == "EN"


class TestHelperEdges:
    def test_scalar_parsers_handle_empty_invalid_and_partial_dates(self):
        from animedex.backends.ann import models

        assert models._parse_optional_int(None) is None
        assert models._parse_optional_int("not-an-int") is None
        assert models._parse_optional_int("12") == 12
        assert models._parse_vintage_start(None) is None
        assert models._parse_vintage_start("2023") == date(2023, 1, 1)
        assert models._parse_vintage_start("2023-09") == date(2023, 9, 1)
        assert models._parse_vintage_start("2023-09-29") == date(2023, 9, 29)
        assert models._parse_vintage_start("unknown") is None
        assert models._normalise_format(None) is None
        assert models._normalise_format("TV") == "TV"
        assert models._normalise_format("web short") is None


class TestSelftest:
    def test_package_and_model_selftests_run(self):
        from animedex.backends import ann
        from animedex.backends.ann import models

        assert models.selftest() is True
        assert ann.selftest() is True
