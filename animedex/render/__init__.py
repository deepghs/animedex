"""
Source-attributed renderers for animedex output.

The renderers are the project's promise to the user: every datum on
the screen carries a visible source. The TTY renderer prints
``[src: <backend>]`` next to each value; the JSON renderer carries
``_source`` annotations and a top-level ``_meta`` block. ``--json
field1,field2`` projects fields, ``--jq <expr>`` post-processes via
the jq subprocess.

The renderers consume :mod:`animedex.models` instances; they never
talk to the wire and never mutate state.
"""
