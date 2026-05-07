"""
Local SQLite cache for animedex backend responses.

The cache is keyed by ``(backend, request_signature)`` and stores
arbitrary bytes per row, with a per-row TTL. Backend modules use it
to keep the upstream call rate well under the P1 caps from
``plans/02`` and to make ``--no-cache`` and ``--cache <ttl>`` flags
straightforward to honour.

The submodule split is deliberately thin:

* :mod:`animedex.cache.sqlite` - the storage engine and the default
  TTL table.

The cache layer never imports any backend module so circular-import
issues do not arise.
"""
