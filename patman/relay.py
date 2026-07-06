# SPDX-License-Identifier: GPL-2.0+
#
# Copyright 2026 Simon Glass <sjg@chromium.org>
#
"""Send patches through a web submission endpoint (b4-style relay)

Instead of 'git send-email', patman can POST a prepared series to a web
relay that sends the mail on the contributor's behalf. This helps people
who have no working outbound SMTP (blocked ports, a provider that mangles
patches, etc.).

Each message is attested with patatt, which adds an X-Developer-Signature
header (a DKIM-style signature). The endpoint authenticates submissions by
that signature -- there is no per-request token -- so a key registered
with the endpoint is what makes a submission trusted.

The wire protocol matches b4's web endpoint (see send_mail() in b4's
src/b4/__init__.py)::

    POST <endpoint>
    {"action": "receive"|"reflect", "messages": [<raw signed message>, ...]}
    -> {"result": "success"} | {"result": "error", "message": ...}
"""

import json
import urllib.error
import urllib.request

from u_boot_pylib import tout

# kernel.org's endpoint (only usable for kernel.org-hosted projects); other
# projects configure their own via the 'send_endpoint_web' setting
DEFAULT_ENDPOINT = 'https://lkml.kernel.org/_b4_submit'


def check_available():
    """Check whether patatt is importable (needed to sign messages)

    Returns:
        bool: True if the patatt library is installed
    """
    try:
        import patatt  # noqa: F401  pylint: disable=C0415,W0611
        return True
    except ImportError:
        return False


def sign_message(msg_bytes):
    """Attest a message with patatt

    Adds an X-Developer-Signature header using the key configured for
    patatt (git 'user.signingKey' for PGP, or a '[patatt]' section).

    Args:
        msg_bytes (bytes): The raw RFC2822 message

    Returns:
        bytes: The message with the signature header added
    """
    import patatt  # pylint: disable=C0415
    return patatt.rfc2822_sign(msg_bytes)


def submit(endpoint, messages, reflect=False):
    """Submit already-signed messages to a web relay

    Args:
        endpoint (str): Submission endpoint URL
        messages (list of str): Raw RFC2822 messages, each already
            patatt-signed
        reflect (bool): True to reflect the series back to the sender only
            (a safe dry run), rather than actually sending it

    Returns:
        int: Number of messages the endpoint accepted

    Raises:
        ValueError: if the endpoint is unreachable, returns a non-JSON
            response, or reports an error
    """
    action = 'reflect' if reflect else 'receive'
    body = json.dumps({'action': action, 'messages': list(messages)}).encode()
    tout.info(f"{'Reflecting' if reflect else 'Sending'} {len(messages)} "
              f'message(s) via {endpoint}')
    req = urllib.request.Request(
        endpoint, data=body, method='POST',
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors='replace')
        raise ValueError(
            f'Relay endpoint HTTP {exc.code}: {detail}') from exc
    except urllib.error.URLError as exc:
        raise ValueError(
            f'Cannot reach relay endpoint {endpoint}: {exc.reason}') from exc

    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ValueError(
            f'Unexpected response from {endpoint}: '
            f'{raw.decode(errors="replace")}') from exc

    if data.get('result') == 'success':
        return len(messages)
    raise ValueError(f"Relay endpoint error: {data.get('message', data)}")
