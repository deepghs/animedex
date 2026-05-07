"""
Token storage for animedex backends.

Per ``plans/02 §7`` the token store lives in the OS keyring; plain
text storage in a dotfile is a security incident, not a UX choice.
This package provides:

* :mod:`animedex.auth.store` - the small :class:`TokenStore`
  Protocol every backend depends on.
* :mod:`animedex.auth.inmemory_store` - an in-memory implementation
  used by unit tests and headless CI environments where the OS
  keyring has no backend.
* :mod:`animedex.auth.keyring_store` - the production implementation
  on top of the ``keyring`` package.

Backends never reach into the keyring directly; they accept a
:class:`TokenStore` from :mod:`animedex.config.profile.Config` and
go through the Protocol. This keeps the secrets path testable and
the substrate layered.
"""
