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

import email.policy
import email.utils
import json
import subprocess
import urllib.error
import urllib.request

from u_boot_pylib import tout

# kernel.org's endpoint (only usable for kernel.org-hosted projects); other
# projects configure their own via the 'send_endpoint_web' setting
DEFAULT_ENDPOINT = 'https://lkml.kernel.org/_b4_submit'

# Shown when patatt has no signing key configured
_NO_KEY_HELP = (
    'No patatt signing key is configured. Set one with:\n'
    '  git config --global patatt.signingkey openpgp:<your-key-id>\n'
    "or create an ed25519 key with 'patatt genkey' and add the printed\n"
    '[patatt] section to your git config.')


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
    try:
        return patatt.rfc2822_sign(msg_bytes)
    except patatt.NoKeyError as exc:
        raise ValueError(_NO_KEY_HELP) from exc
    except patatt.SigningError as exc:
        raise ValueError(
            f'patatt failed to sign the message: {exc}. Check that the '
            'signing key is usable non-interactively (e.g. gpg-agent is '
            'running and the passphrase is cached or available)') from exc


def _post(endpoint, req):
    """POST a JSON request to the endpoint and return the parsed response

    Args:
        endpoint (str): Endpoint URL
        req (dict): Request body to send as JSON

    Returns:
        dict: The decoded JSON response

    Raises:
        ValueError: if the endpoint is unreachable, returns a non-JSON
            response, or reports a result other than 'success'
    """
    body = json.dumps(req).encode()
    http_req = urllib.request.Request(
        endpoint, data=body, method='POST',
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(http_req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors='replace')
        raise ValueError(f'Endpoint HTTP {exc.code}: {detail}') from exc
    except urllib.error.URLError as exc:
        raise ValueError(
            f'Cannot reach endpoint {endpoint}: {exc.reason}') from exc

    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ValueError(
            f'Unexpected response from {endpoint}: '
            f'{raw.decode(errors="replace")}') from exc

    if data.get('result') != 'success':
        raise ValueError(f"Endpoint error: {data.get('message', data)}")
    return data


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
        ValueError: if the endpoint is unreachable or reports an error
    """
    action = 'reflect' if reflect else 'receive'
    tout.info(f"{'Reflecting' if reflect else 'Sending'} {len(messages)} "
              f'message(s) via {endpoint}')
    _post(endpoint, {'action': action, 'messages': list(messages)})
    return len(messages)


def _git_config(key):
    """Read a git config value, returning '' if it is unset"""
    result = subprocess.run(['git', 'config', key], check=False,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True)
    return result.stdout.strip()


def _derive_pubkey(algo, keydata):
    """Derive the public key to register from the patatt signing key

    Args:
        algo (str): patatt algorithm, 'openpgp' or 'ed25519'
        keydata (str): The signing key data from patatt's config

    Returns:
        str: The public key (armoured PGP, or base64 ed25519)

    Raises:
        ValueError: if the algorithm is unsupported or export fails
    """
    if algo == 'openpgp':
        result = subprocess.run(
            ['gpg', '--export', '--export-options', 'export-minimal', '-a',
             keydata],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode or not result.stdout:
            raise ValueError(f'Unable to export PGP public key for {keydata}')
        return result.stdout.decode()
    if algo == 'ed25519':
        import base64
        from nacl.encoding import Base64Encoder
        from nacl.signing import SigningKey
        skey = SigningKey(keydata.encode(), encoder=Base64Encoder)
        return base64.b64encode(skey.verify_key.encode()).decode()
    raise ValueError(
        f"Unsupported patatt algorithm '{algo}' for web submission")


def _auth_config():
    """Gather the identity and key info needed to register with an endpoint

    Returns:
        tuple: (name, identity, selector, pubkey) where identity is the
            email address

    Raises:
        ValueError: if no email or signing key is configured
    """
    import patatt
    identity = _git_config('user.email')
    if not identity:
        raise ValueError('No email configured; set git user.email')
    name = _git_config('user.name')
    pconfig = patatt.get_main_config()
    selector = str(pconfig.get('selector', 'default'))
    try:
        algo, keydata = patatt.get_algo_keydata(pconfig)
    except patatt.NoKeyError as exc:
        raise ValueError(_NO_KEY_HELP) from exc
    return name, identity, selector, _derive_pubkey(algo, keydata)


def auth_new(endpoint):
    """Start endpoint registration: request an emailed challenge

    Sends your name, identity and public key to the endpoint, which
    replies by emailing a challenge to your address. Complete it with
    auth_verify().

    Args:
        endpoint (str): Web submission endpoint URL

    Raises:
        ValueError: on a configuration or endpoint error
    """
    name, identity, selector, pubkey = _auth_config()
    tout.notice(f'Requesting email authorisation from {endpoint}')
    tout.notice(f'  Name:     {name}')
    tout.notice(f'  Identity: {identity}')
    tout.notice(f'  Selector: {selector}')
    _post(endpoint, {
        'action': 'auth-new',
        'name': name,
        'identity': identity,
        'selector': selector,
        'pubkey': pubkey,
    })
    tout.notice(f'Challenge sent to {identity}. When it arrives, run:')
    tout.notice('  patman send --web-auth-verify <challenge>')


def auth_verify(endpoint, challenge):
    """Complete registration by signing and returning the challenge

    Builds a minimal message containing the challenge, signs it with
    patatt and posts it to the endpoint, proving control of both the From
    address and the key.

    Args:
        endpoint (str): Web submission endpoint URL
        challenge (str): The challenge string from the endpoint's email

    Raises:
        ValueError: on a configuration or endpoint error
    """
    from email.message import EmailMessage
    _, identity, _, _ = _auth_config()
    # The endpoint requires this exact message shape: a 'b4-send-verify'
    # subject and an 8-bit 'verify:<challenge>' body, serialised the same
    # way b4 does (utf8, 8-bit, no line wrapping)
    msg = EmailMessage()
    msg['From'] = identity
    msg['Subject'] = 'b4-send-verify'
    msg['Message-ID'] = email.utils.make_msgid(domain='b4')
    # Use set_content() so the body is a well-formed text/plain part;
    # set_charset()/set_payload() can produce a base64 header with a
    # plaintext body on some Python versions, which the endpoint rejects
    msg.set_content(f'verify:{challenge}\n')
    policy = email.policy.EmailPolicy(utf8=True, cte_type='8bit',
                                      max_line_length=None)
    signed = sign_message(msg.as_bytes(policy=policy)).decode()
    _post(endpoint, {'action': 'auth-verify', 'msg': signed})
    tout.notice(f'Challenge verified for {identity}; the endpoint is ready '
                'for sending.')
