Changelog
=========

All notable changes to this project are documented here. The format is
based on `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`_ and
the project follows `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

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
