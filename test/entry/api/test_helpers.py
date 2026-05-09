"""Coverage tests for the small helpers in
:mod:`animedex.entry.api`.

Each helper is exercised directly so codecov can attribute the
behaviour to a specific test rather than indirectly through CLI
runner flows.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unittest


def _make_envelope(status: int, *, firewall: bool = False):
    """Build a minimal :class:`RawResponse` for routing tests."""
    from animedex.api._envelope import RawCacheInfo, RawRequest, RawResponse, RawTiming

    return RawResponse(
        backend="jikan",
        request=RawRequest(method="GET", url="https://x.invalid/", headers={}),
        status=status,
        response_headers={},
        body_bytes=b"",
        body_text="",
        timing=RawTiming(total_ms=0.0, rate_limit_wait_ms=0.0, request_ms=0.0),
        cache=RawCacheInfo(hit=False),
        firewall_rejected=({"reason": "unknown-backend", "message": "x"} if firewall else None),
    )


class TestOutputModeFromFlags:
    def test_no_flag_returns_body(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(False, False, False) == "body"

    def test_include_flag(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(True, False, False) == "include"

    def test_head_flag(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(False, True, False) == "head"

    def test_debug_flag(self):
        from animedex.entry.api import _output_mode_from_flags

        assert _output_mode_from_flags(False, False, True) == "debug"

    def test_two_flags_set_raises(self):
        import click

        from animedex.entry.api import _output_mode_from_flags

        with pytest.raises(click.UsageError, match="mutually exclusive"):
            _output_mode_from_flags(True, True, False)

    def test_three_flags_set_raises(self):
        import click

        from animedex.entry.api import _output_mode_from_flags

        with pytest.raises(click.UsageError, match="mutually exclusive"):
            _output_mode_from_flags(True, True, True)


class TestRenderOutput:
    def test_body_mode(self):
        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="body", full_body=False)
        assert isinstance(out, str)

    def test_include_mode_has_status_line(self):
        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="include", full_body=False)
        assert "200" in out.split("\n", 1)[0]

    def test_head_mode_omits_body(self):
        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="head", full_body=False)
        # head mode contains only the status line + headers; no JSON
        # body. The empty body is empty, so a sanity check that
        # status appears suffices.
        assert "200" in out

    def test_debug_mode_emits_json(self):
        import json

        from animedex.entry.api import _render_output

        out = _render_output(_make_envelope(200), mode="debug", full_body=False)
        decoded = json.loads(out)
        assert decoded["status"] == 200


class TestExitCodeFor:
    @pytest.mark.parametrize(
        "status,expected",
        [
            (200, 0),
            (201, 0),
            (299, 0),
            (301, 3),
            (399, 3),
            (400, 4),
            (404, 4),
            (499, 4),
            (500, 5),
            (503, 5),
            (599, 5),
            (100, 1),
            (700, 1),
        ],
    )
    def test_status_class_to_exit_code(self, status, expected):
        from animedex.entry.api import _exit_code_for

        assert _exit_code_for(_make_envelope(status)) == expected

    def test_local_rejection_overrides_status(self):
        from animedex.entry.api import _exit_code_for

        # Locally rejected envelopes have status=0, but the exit code
        # comes from the rejection flag, not the status class.
        assert _exit_code_for(_make_envelope(0, firewall=True)) == 2


class TestParseExtraHeaders:
    def test_empty_returns_empty_dict(self):
        from animedex.entry.api import _parse_extra_headers

        assert _parse_extra_headers(()) == {}
        assert _parse_extra_headers(None) == {}

    def test_single_header(self):
        from animedex.entry.api import _parse_extra_headers

        assert _parse_extra_headers(("X-Foo: bar",)) == {"X-Foo": "bar"}

    def test_multiple_headers(self):
        from animedex.entry.api import _parse_extra_headers

        out = _parse_extra_headers(("X-Foo: bar", "User-Agent: my-bot/1"))
        assert out == {"X-Foo": "bar", "User-Agent": "my-bot/1"}

    def test_value_with_colon(self):
        """Only the first colon is the separator; the rest is the
        value (e.g. 'Date: Thu, 07 May 2026 13:39:30')."""
        from animedex.entry.api import _parse_extra_headers

        out = _parse_extra_headers(("Date: Thu, 07 May 13:39:30",))
        assert out == {"Date": "Thu, 07 May 13:39:30"}

    def test_malformed_raises(self):
        import click

        from animedex.entry.api import _parse_extra_headers

        with pytest.raises(click.UsageError, match="must be 'Name: Value'"):
            _parse_extra_headers(("no-colon-here",))


class TestParseApiFields:
    def test_typed_values_and_raw_strings(self):
        from animedex.entry.api import _parse_api_fields

        assert _parse_api_fields(
            (
                ("typed", "count=10"),
                ("typed", "score=9.5"),
                ("typed", "published=true"),
                ("typed", "airing=false"),
                ("typed", "title=Frieren"),
                ("raw", "tag=true"),
            )
        ) == {"count": 10, "score": 9.5, "published": True, "airing": False, "title": "Frieren", "tag": "true"}

    def test_last_write_wins_across_kinds(self):
        from animedex.entry.api import _parse_api_fields

        assert _parse_api_fields((("typed", "count=1"), ("raw", "count=10"))) == {"count": "10"}
        assert _parse_api_fields((("raw", "count=1"), ("typed", "count=10"))) == {"count": 10}

    def test_malformed_field_raises(self):
        import click

        from animedex.entry.api import _parse_api_fields

        with pytest.raises(click.UsageError, match="must be K=V"):
            _parse_api_fields((("typed", "broken"),))

    def test_empty_key_raises(self):
        import click

        from animedex.entry.api import _parse_api_fields

        with pytest.raises(click.UsageError, match="key must not be empty"):
            _parse_api_fields((("typed", "=broken"),))


class TestApiFieldParserHelpers:
    def test_normalize_option_without_context_normalizer(self):
        from animedex.entry.api import _normalize_option

        assert _normalize_option("--raw-field", object()) == "--raw-field"

    def test_normalize_option_with_context_normalizer(self):
        from animedex.entry.api import _normalize_option

        class Ctx:
            token_normalize_func = staticmethod(str.upper)

        assert _normalize_option("--raw-field", Ctx()) == "--RAW-FIELD"
        assert _normalize_option("-f", Ctx()) == "-F"

    @pytest.mark.parametrize(
        "option,expected",
        [
            ("--raw-field", {"--"}),
            ("-f", {"-"}),
            ("field", set()),
        ],
    )
    def test_option_prefixes(self, option, expected):
        from animedex.entry.api import _option_prefixes

        assert _option_prefixes(option) == expected

    def test_parser_option_process_calls_wrapped_callback(self):
        from animedex.entry.api import _ApiFieldParserOption

        sentinel = object()
        captured = []
        option = _ApiFieldParserOption(
            obj=type("Obj", (), {"name": "api_fields"})(),
            opts=["-f"],
            process_value=lambda opts, value, state: captured.append((opts, value, state)),
        )
        option.process("x=1", state=sentinel)
        assert captured == [(["-f"], "x=1", sentinel)]

    def test_api_field_option_fetches_value_from_state_when_click_omits_it(self):
        from animedex.entry.api import ApiFieldOption

        class Parser:
            def __init__(self):
                self._long_opt = {}
                self._short_opt = {}
                self._opt_prefixes = set()

            def _get_value_from_state(self, opt, parser_option, state):
                assert opt == "--field"
                assert parser_option is self._long_opt["--field"]
                assert state is sentinel
                return "limit=2"

        class State:
            def __init__(self):
                self.opts = {}
                self.order = []

        sentinel = State()
        parser = Parser()
        option = ApiFieldOption(("--field",), expose_kind="typed")

        option.add_to_parser(parser, object())
        parser._long_opt["--field"].process(None, sentinel)

        assert sentinel.opts == {option.name: [("typed", "limit=2")]}
        assert sentinel.order == [option]

    def test_api_field_option_type_cast_none(self):
        from animedex.entry.api import ApiFieldOption

        option = ApiFieldOption(("--field",), expose_kind="typed")
        assert option.type_cast_value(None, None) == ()


class TestMergePathAndFields:
    def test_no_fields_returns_original_path_and_no_params(self):
        from animedex.entry.api import _merge_path_and_fields

        assert _merge_path_and_fields("/anime?q=Naruto", {}) == ("/anime?q=Naruto", None)

    def test_fields_merge_over_path_query(self):
        from animedex.entry.api import _merge_path_and_fields

        path, params = _merge_path_and_fields("/anime?q=Frieren&limit=1", {"q": "Naruto"})
        assert path == "/anime"
        assert params == {"q": "Naruto", "limit": "1"}


class TestMergeJsonObjects:
    def test_left_none_and_right_none_returns_empty_dict(self):
        from animedex.entry.api import _merge_json_objects

        assert _merge_json_objects(None, None, left_name="left", right_name="right") == {}

    def test_left_dict_and_right_none_returns_copy(self):
        from animedex.entry.api import _merge_json_objects

        left = {"a": 1}
        out = _merge_json_objects(left, None, left_name="left", right_name="right")
        assert out == {"a": 1}
        assert out is not left

    def test_right_overrides_left(self):
        from animedex.entry.api import _merge_json_objects

        assert _merge_json_objects({"a": 1}, {"a": 2, "b": 3}, left_name="left", right_name="right") == {
            "a": 2,
            "b": 3,
        }

    def test_non_object_left_raises(self):
        import click

        from animedex.entry.api import _merge_json_objects

        with pytest.raises(click.UsageError, match="left must decode"):
            _merge_json_objects([], {}, left_name="left", right_name="right")

    def test_non_object_right_raises(self):
        import click

        from animedex.entry.api import _merge_json_objects

        with pytest.raises(click.UsageError, match="right must decode"):
            _merge_json_objects({}, [], left_name="left", right_name="right")


class TestCallOrPaginate:
    def test_plain_call_delegates_to_backend_module(self):
        from animedex.entry.api import _call_or_paginate

        class Backend:
            @staticmethod
            def call(**kwargs):
                return {"kwargs": kwargs}

        assert _call_or_paginate(
            Backend,
            backend="jikan",
            paginate=False,
            max_pages=10,
            max_items=None,
            path="/anime",
        ) == {"kwargs": {"path": "/anime"}}

    def test_unsupported_paginate_backend_falls_back_to_raw_call(self, capsys):
        from animedex.entry.api import _call_or_paginate

        class Backend:
            @staticmethod
            def call(**kwargs):
                return {"kwargs": kwargs}

        assert _call_or_paginate(
            Backend,
            backend="anilist",
            paginate=True,
            max_pages=10,
            max_items=None,
            path="/",
            method="GET",
        ) == {"kwargs": {"path": "/", "method": "GET"}}
        assert (
            "--paginate ignored: backend 'anilist' has no pagination strategy; sending a single forwarded request."
            in capsys.readouterr().err
        )

    def test_unsupported_paginate_backend_with_explicit_non_get_falls_back_to_raw_call(self, capsys):
        from animedex.entry.api import _call_or_paginate

        class Backend:
            @staticmethod
            def call(**kwargs):
                return {"kwargs": kwargs}

        assert _call_or_paginate(
            Backend,
            backend="anilist",
            paginate=True,
            max_pages=10,
            max_items=None,
            method_explicit=True,
            path="/",
            method="POST",
        ) == {"kwargs": {"path": "/", "method": "POST"}}
        assert "--paginate ignored: explicit -X POST; sending a single forwarded request." in capsys.readouterr().err

    def test_non_get_paginate_falls_back_to_raw_call(self, capsys):
        from animedex.entry.api import _call_or_paginate

        class Backend:
            @staticmethod
            def call(**kwargs):
                return {"kwargs": kwargs}

        assert _call_or_paginate(
            Backend,
            backend="jikan",
            paginate=True,
            max_pages=10,
            max_items=None,
            path="/anime",
            method="POST",
        ) == {"kwargs": {"path": "/anime", "method": "POST"}}
        assert "--paginate ignored: explicit -X POST; sending a single forwarded request." in capsys.readouterr().err

    def test_paginate_api_error_becomes_click_exception(self):
        import click

        from animedex.entry.api import _call_or_paginate

        class Backend:
            @staticmethod
            def call(**kwargs):
                return {"kwargs": kwargs}

        with pytest.raises(click.ClickException, match="--max-pages must be >= 1"):
            _call_or_paginate(
                Backend,
                backend="jikan",
                paginate=True,
                max_pages=0,
                max_items=None,
                path="/anime",
                method="GET",
            )


class TestEmit:
    def test_echoes_rendered_output_and_exits_with_status_class_code(self):
        import click
        from click.testing import CliRunner

        from animedex.entry.api import _emit

        @click.command()
        def cmd():
            ctx = click.get_current_context()
            _emit(ctx, _make_envelope(404), mode="body", full_body=False)

        result = CliRunner().invoke(cmd, [])
        assert result.exit_code == 4

    def test_local_rejection_envelope_exits_2(self):
        import click
        from click.testing import CliRunner

        from animedex.entry.api import _emit

        @click.command()
        def cmd():
            ctx = click.get_current_context()
            _emit(ctx, _make_envelope(0, firewall=True), mode="body", full_body=False)

        result = CliRunner().invoke(cmd, [])
        assert result.exit_code == 2


class TestResolveCache:
    def test_no_cache_returns_none(self):
        from animedex.entry.api import _resolve_cache

        assert _resolve_cache(no_cache=True) is None

    def test_default_returns_singleton(self, monkeypatch):
        import animedex.entry.api as entry_api

        sentinel = object()
        monkeypatch.setattr(entry_api, "_default_cache", lambda: sentinel)
        assert entry_api._resolve_cache(no_cache=False) is sentinel
