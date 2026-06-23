Changelog
=========

All notable changes to this project are documented here. The format is
based on `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`_ and
the project follows `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

Added
~~~~~
- ``review --redraft`` recreates the Gmail drafts from the stored
  reviews even when a draft already exists, to recover after an error.

0.0.11 - 2026-06-18
-------------------

Added
~~~~~
- A project logo, shown in the documentation and the README.

Fixed
~~~~~
- ``autolink`` finds a series whose cover-letter title changed in a
  later version: it searches patchwork by the current title rather than
  the title recorded when the version was created.

0.0.10 - 2026-06-15
-------------------

Fixed
~~~~~
- ``status --dest-branch`` (building a branch with the gathered review
  tags) works again on pygit2 1.16 and newer, where ``merge_trees()``
  no longer accepts a branch object.

0.0.9 - 2026-06-15
------------------

Fixed
~~~~~
- ``series status`` and ``gather`` now work on archived series, reading
  the patches from the archive tag rather than the deleted branch.

Changed
~~~~~~~
- Update the pinned dependencies to current releases and support the
  pygit2 1.15 API.
- Reorganise the documentation: it lives under ``doc/``, includes the
  changelog, can be built with ``make -C doc html``, and reads as a
  general patch tool rather than a U-Boot-specific one.

0.0.8 - 2026-06-08
------------------

Added
~~~~~
- ``patman review -c/--context`` passes extra notes to the review agent
  for a single run -- either a literal string or ``@path`` to read the
  text from a file.
- ``patman series changes <text>`` records a ``Series-changes`` (or,
  with ``-c``, ``Cover-changes``) bullet on the HEAD commit and amends
  it, instead of hand-editing the commit message.
- Documentation is now published at https://patman.readthedocs.io/.

Changed
~~~~~~~
- Follow-up reviews respect the "say it in v1" convention: later
  versions confirm whether earlier feedback was addressed rather than
  piling on fresh nits.
- A partial patch apply now warns and continues with whatever applied,
  instead of aborting and discarding the work.
- Patman is now distributed as the self-contained ``patch-manager``
  package, with ``u_boot_pylib`` vendored in, installable from PyPI
  with ``pip install patch-manager``.

Earlier releases
----------------

Releases 0.0.7 and earlier predate this changelog.
