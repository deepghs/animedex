"""Phase-2 TTY render coverage: Character / Staff / Studio /
TraceHit / TraceQuota."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


pytestmark = pytest.mark.unittest


def _src(backend="anilist"):
    from animedex.models.common import SourceTag

    return SourceTag(backend=backend, fetched_at=datetime(2026, 5, 7, tzinfo=timezone.utc))


class TestCharacterTty:
    def test_full_character_renders(self):
        from animedex.models.character import Character
        from animedex.models.common import PartialDate
        from animedex.render.tty import render_tty

        c = Character(
            id="anilist:char:36",
            name="Edward Elric",
            name_native="エドワード・エルリック",
            name_alternatives=["Ed", "Fullmetal"],
            role="MAIN",
            image_url="https://x.invalid/c.jpg",
            description="d",
            gender="Male",
            age="15",
            date_of_birth=PartialDate(year=1899, month=2, day=3),
            favourites=12345,
            source=_src(),
        )
        out = render_tty(c)
        assert "Edward Elric" in out
        assert "[src: anilist]" in out
        assert "Native:" in out
        assert "Alt names" in out
        assert "MAIN" in out
        assert "Male" in out
        assert "Favourites: 12,345" in out

    def test_minimal_character_renders(self):
        from animedex.models.character import Character
        from animedex.render.tty import render_tty

        c = Character(id="anilist:char:1", name="x", source=_src())
        out = render_tty(c)
        assert "[src: anilist]" in out
        assert out.startswith("x")
        assert "Native:" not in out  # absent fields skipped


class TestStaffTty:
    def test_full_staff_renders(self):
        from animedex.models.character import Staff
        from animedex.render.tty import render_tty

        s = Staff(
            id="anilist:staff:1",
            name="Naoko Yamada",
            name_native="山田尚子",
            occupations=["Director", "Storyboard"],
            language="Japanese",
            home_town="Kyoto",
            years_active=[2004],
            favourites=5000,
            source=_src(),
        )
        out = render_tty(s)
        assert "Naoko Yamada" in out
        assert "Director" in out
        assert "Japanese" in out
        assert "Kyoto" in out


class TestStudioTty:
    def test_studio_renders(self):
        from animedex.models.character import Studio
        from animedex.render.tty import render_tty

        s = Studio(id="anilist:studio:11", name="MADHOUSE", is_animation_studio=True, favourites=12345, source=_src())
        out = render_tty(s)
        assert "MADHOUSE" in out
        assert "yes" in out  # is_animation_studio renders as yes/no
        assert "12,345" in out  # favourites formatted with thousands separator


class TestTraceHitTty:
    def test_with_inline_title(self):
        from animedex.models.anime import AnimeTitle
        from animedex.models.trace import TraceHit
        from animedex.render.tty import render_tty

        h = TraceHit(
            anilist_id=154587,
            anilist_title=AnimeTitle(romaji="Sousou no Frieren"),
            similarity=0.9876,
            episode="3",
            start_at_seconds=120.0,
            frame_at_seconds=121.5,
            end_at_seconds=123.0,
            episode_filename="x.mkv",
            preview_video_url="https://x.invalid/v",
            source=_src(backend="trace"),
        )
        out = render_tty(h)
        assert "Sousou no Frieren" in out
        assert "anilist:154587" in out
        assert "121.50" in out
        assert "0.9876" in out

    def test_without_inline_title(self):
        from animedex.models.trace import TraceHit
        from animedex.render.tty import render_tty

        h = TraceHit(
            anilist_id=1,
            similarity=0.9,
            start_at_seconds=0.0,
            frame_at_seconds=0.5,
            end_at_seconds=1.0,
            source=_src(backend="trace"),
        )
        out = render_tty(h)
        assert "(unknown)" in out
        assert "anilist:1" in out


class TestTraceQuotaTty:
    def test_renders(self):
        from animedex.models.trace import TraceQuota
        from animedex.render.tty import render_tty

        q = TraceQuota(priority=0, concurrency=1, quota=100, quota_used=18, source=_src(backend="trace"))
        out = render_tty(q)
        assert "[src: trace]" in out
        assert "100" in out
        assert "18" in out
