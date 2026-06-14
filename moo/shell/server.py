# -*- coding: utf-8 -*-
"""
AsyncSSH server entrypoint.

See :doc:`/explanation/shell-internals` for the reasoning behind
``line_editor=False``, the keepalive settings, and the signal handlers.
"""

import asyncio
import faulthandler
import json
import logging
import os
import signal
import sys
from typing import cast

import asyncssh
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from prompt_toolkit.contrib.ssh import PromptToolkitSSHServer, PromptToolkitSSHSession
from simplesshkey.models import UserKey

from .iac import IacNegotiator, IacParser, is_known_mud_client
from .prompt import embed

log = logging.getLogger(__name__)

_active_sessions: set[str] = set()
_total_connections: int = 0


def _fd_count() -> int:
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        return -1


_MUD_CLIENT_TERM_MARKERS = ("mudlet", "tintin", "mushclient", "blowtorch", "mudrammer", "zmud", "cmud")

# Delimiter used to encode a Site domain inside the SSH username, e.g.
# ``ssh alice+example.com@host`` routes ``alice`` to the ``example.com`` Site.
# ``+`` is the de-facto convention (sshpiper, etc.) and is allowed in Django
# usernames but not used by any account in this codebase.
USER_SITE_DELIMITER = "+"


def _split_user_suffix(raw_username: str) -> tuple[str, str | None]:
    """Split ``user+sitedomain`` into ``(user, sitedomain)``.

    Returns ``(raw_username, None)`` when no delimiter is present.  SSH has
    no protocol-level hostname indication (no SNI, no Host header — see
    RFCs 4253/4254/8308), so the dialed Site has to ride in the username.
    """
    if USER_SITE_DELIMITER not in raw_username:
        return raw_username, None
    base, _, suffix = raw_username.partition(USER_SITE_DELIMITER)
    suffix = suffix.strip()
    if not base or not suffix:
        return raw_username, None
    return base, suffix


def _iac_bytes_to_str(data: bytes) -> str:
    """
    Convert raw IAC bytes to a str the surrogate-escape UTF-8 channel
    can re-emit verbatim. ``\\xff`` becomes ``\\udcff``, etc.
    """
    return data.decode("utf-8", errors="surrogateescape")


def _is_mud_term(term: str | None) -> bool:
    """
    True when the SSH client's ``TERM`` string signals a MUD client.

    Matches the existing ``xterm-256-basic`` raw-mode opt-in plus a small
    allowlist of major MUD-client `TERM` values. Anything else (xterm,
    tmux, screen, ...) gets a plain rich-mode session with no IAC
    negotiation, since IAC bytes render as garbage in regular terminals.
    """
    if not term:
        return False
    lowered = term.strip().lower()
    if lowered == "xterm-256-basic":
        return True
    return any(marker in lowered for marker in _MUD_CLIENT_TERM_MARKERS)


class MooPromptToolkitSSHSession(PromptToolkitSSHSession):
    """
    SSH session that selects a shell mode from the client's ``TERM`` and
    speaks the IAC subnegotiation channel on top of SSH for MUD clients.

    For MUD clients (TERM = ``xterm-256-basic`` or a known MUD-client
    name), the channel switches its UTF-8 error policy to
    ``surrogateescape`` so 0xFF IAC bytes round-trip as ``\\udcff``
    surrogate code points: outbound IAC frames go out by decoding raw
    bytes through surrogateescape (the channel's UTF-8 encoder
    re-emits them as the original bytes), and inbound 0xFF arrives as
    surrogate chars in :meth:`data_received` which we re-encode for
    the IAC parser. The channel stays in str mode the whole time, so
    prompt_toolkit's renderer, CPR detection, and Stdout pipeline work
    unchanged. Vanilla SSH terminals leave the channel in strict UTF-8
    and never see an IAC byte.

    See :doc:`/explanation/shell-internals` § "The Three Modes" for
    the full mapping.
    """

    user = None  # set by MooSSHServer.session_requested() before the session starts
    site = None  # set by MooSSHServer.session_requested() before the session starts
    mode: str = "rich"
    iac_enabled: bool = False  # set to True in connection_made when TERM looks like a MUD client

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.iac_parser = IacParser()
        self.iac_negotiator = IacNegotiator(
            on_ttype=self._on_ttype,
            on_gmcp=self._on_gmcp,
            on_mssp_request=self._on_mssp_request,
        )

    def _clear_iac_cache(self) -> None:
        """Remove any cached IAC capability snapshot for this user."""
        if self.user is None:
            return
        try:
            from django.core.cache import cache  # pylint: disable=import-outside-toplevel

            from .prompt import _session_settings  # pylint: disable=import-outside-toplevel

            _session_settings.get(self.user.pk, {}).pop("iac", None)
            cache.delete(f"moo:session:{self.user.pk}:iac")
        except Exception:  # pylint: disable=broad-except
            log.exception("failed to clear stale IAC cache for user=%s", self.user)

    def session_started(self) -> None:
        # All TERM-dependent setup happens here, not in connection_made:
        # asyncssh populates the terminal type from the client's PTY request,
        # which arrives between connection_made and session_started.
        if self._chan:
            term = self._chan.get_terminal_type()
            if term and term.strip().lower() == "xterm-256-basic":
                self.mode = "raw"
            self.iac_enabled = _is_mud_term(term)
            if self.iac_enabled:
                # Lenient UTF-8 so 0xFF IAC bytes round-trip as \udcff
                # surrogates; the channel stays in str mode so prompt_toolkit's
                # renderer and CPR detection work unchanged.
                self._chan.set_encoding("utf-8", errors="surrogateescape")
            else:
                # Clear any stale IAC capability cache from a previous
                # MUD-client session — send_gmcp would otherwise return True
                # via _client_supports for the next 24h and try to publish
                # OOB events the current client cannot consume.
                self._clear_iac_cache()
        super().session_started()
        # Initial IAC option offers go out only when we're talking to a MUD
        # client; vanilla SSH would render the offer bytes as garbage
        # characters. The channel is in surrogate-escape UTF-8 mode for MUD
        # clients, so we feed it str.
        negotiator = getattr(self, "iac_negotiator", None)
        if self.iac_enabled and negotiator is not None and self._chan is not None:
            try:
                self._chan.write(_iac_bytes_to_str(negotiator.initial_offers()))
            except BrokenPipeError:
                pass

    def data_received(self, data, datatype) -> None:  # type: ignore[override]
        # Vanilla SSH clients (no MUD-client TERM) — just forward as-is.
        if not self.iac_enabled:
            if self._input is not None and isinstance(data, str):
                self._input.send_text(data)
            return

        # MUD-client path: data is str with possible \udcXX surrogates from
        # surrogateescape decoding. Re-encode to bytes for IAC parsing.
        if isinstance(data, str):
            data_bytes = data.encode("utf-8", errors="surrogateescape")
        else:
            data_bytes = bytes(data)

        events, residual_bytes = self.iac_parser.feed(data_bytes)
        if events:
            prev_caps = dict(self.iac_negotiator.capabilities)
            for event in events:
                reply = self.iac_negotiator.handle(event)
                if reply and self._chan is not None:
                    try:
                        self._chan.write(_iac_bytes_to_str(reply))
                    except BrokenPipeError:
                        return
            # Mirror to _session_settings + cache whenever any capability flipped,
            # not just when TTYPE finalizes — a client may enable GMCP via DO
            # without ever running the TTYPE dance.
            if self.iac_negotiator.capabilities != prev_caps:
                self._mirror_capabilities()
        if residual_bytes and self._input is not None:
            self._input.send_text(residual_bytes.decode("utf-8", errors="surrogateescape"))

    # --- IAC callbacks ------------------------------------------------------

    def _mirror_capabilities(self) -> None:
        """Copy negotiated IAC capabilities into the per-user session settings and cache.

        Preserves ``gmcp_packages`` if it was set previously by
        ``_record_gmcp_supports`` -- the negotiator only knows about
        IAC-level flags (gmcp, ttype, mtts, client_name, ...), so
        replacing the whole ``iac`` dict on every capability flip would
        wipe the GMCP package map that arrived via ``Core.Supports.Set``.
        """
        if self.user is None:
            return
        from django.core.cache import cache  # pylint: disable=import-outside-toplevel

        from .prompt import _session_settings  # pylint: disable=import-outside-toplevel

        caps = dict(self.iac_negotiator.capabilities)
        existing = _session_settings.get(self.user.pk, {}).get("iac")
        if isinstance(existing, dict) and "gmcp_packages" in existing:
            caps["gmcp_packages"] = existing["gmcp_packages"]
        _session_settings.setdefault(self.user.pk, {})["iac"] = caps
        # Mirror to cache so Celery workers (separate process) can see it.
        cache.set(f"moo:session:{self.user.pk}:iac", caps, timeout=86400)

    def _on_ttype(self, client_name: str, mtts: int) -> None:
        # Capability mirroring happens in data_received after handle() runs;
        # this callback only records the MUD-client detection for mode-select
        # logic on the next connection.
        if is_known_mud_client(client_name):
            log.info("MTTS detected MUD client user=%s name=%s mtts=%d", self.user, client_name, mtts)

    def _on_gmcp(self, module: str, data: object) -> None:
        """
        Dispatch inbound GMCP packages.

        Currently recognised:

        - ``Core.Supports.Set`` / ``Core.Supports.Add`` / ``Core.Supports.Remove``:
          track the client's supported GMCP packages so server-side code
          (e.g. ``can_open_editor``) can decide whether to use rich features
          like the GMCP-based editor handoff.
        - ``Editor.Save``: a previously-issued ``Editor.Start`` has completed
          on the client side; invoke the stored callback verb with the new
          content via Celery (same dispatch path as the prompt-toolkit editor).
        - ``Editor.Cancel``: discard the pending edit without invoking the
          callback.

        Anything else is logged at debug level.
        """
        log.debug("GMCP recv user=%s module=%s data=%r", self.user, module, data)
        if module in ("Core.Supports.Set", "Core.Supports.Add", "Core.Supports.Remove"):
            self._record_gmcp_supports(module, data)
        elif module == "Editor.Save":
            self._dispatch_editor_save(data)
        elif module == "Editor.Cancel":
            self._dispatch_editor_cancel(data)

    def _record_gmcp_supports(self, module: str, data: object) -> None:
        """
        Apply a ``Core.Supports.{Set,Add,Remove}`` payload to the per-session
        GMCP package map. Each entry in ``data`` is a string of the form
        ``"<package> <version>"`` (Remove may omit the version).
        """
        if not isinstance(data, list) or self.user is None:
            return
        from django.core.cache import cache  # pylint: disable=import-outside-toplevel

        from .prompt import _session_settings  # pylint: disable=import-outside-toplevel

        settings = _session_settings.setdefault(self.user.pk, {})
        iac = settings.setdefault("iac", {})
        pkgs = iac.setdefault("gmcp_packages", {})
        if module == "Core.Supports.Set":
            pkgs.clear()
        if module in ("Core.Supports.Set", "Core.Supports.Add"):
            for entry in data:
                if not isinstance(entry, str):
                    continue
                parts = entry.split(None, 1)
                if not parts:
                    continue
                name = parts[0]
                try:
                    version = int(parts[1]) if len(parts) > 1 else 1
                except ValueError:
                    version = 1
                pkgs[name] = version
        elif module == "Core.Supports.Remove":
            for entry in data:
                if isinstance(entry, str) and entry:
                    pkgs.pop(entry.split(None, 1)[0], None)
        cache.set(f"moo:session:{self.user.pk}:iac", iac, timeout=86400)
        log.info("GMCP %s user=%s pkgs=%r", module, self.user, pkgs)

    def _dispatch_editor_save(self, data: object) -> None:
        """
        Invoke the callback verb stored when ``Editor.Start`` was sent.
        ``data`` is expected to be ``{"id": "<edit_id>", "content": "..."}``.
        """
        if not isinstance(data, dict) or self.user is None:
            return
        edit_id = data.get("id")
        content = data.get("content")
        if not edit_id or not isinstance(content, str):
            log.warning("Editor.Save user=%s missing id or content: %r", self.user, data)
            return

        from moo.core import models, tasks  # pylint: disable=import-outside-toplevel

        from .prompt import _session_settings  # pylint: disable=import-outside-toplevel

        pending = _session_settings.get(self.user.pk, {}).get("pending_edits", {})
        req = pending.pop(edit_id, None)
        if req is None:
            log.warning("Editor.Save user=%s unknown edit_id=%s", self.user, edit_id)
            return
        try:
            caller = models.Object.objects.get(pk=req["caller_id"])
        except models.Object.DoesNotExist:
            log.warning("Editor.Save user=%s caller_id=%s not found", self.user, req["caller_id"])
            return
        if not caller.is_wizard():
            log.warning(
                "Editor.Save user=%s rejected callback with non-wizard caller_id=%s", self.user, req["caller_id"]
            )
            return
        tasks.invoke_verb.delay(
            content,
            *req.get("args", []),
            caller_id=req["caller_id"],
            player_id=req["player_id"],
            this_id=req["callback_this_id"],
            verb_name=req["callback_verb_name"],
        )

    def _dispatch_editor_cancel(self, data: object) -> None:
        """Drop the pending edit without invoking the callback."""
        if not isinstance(data, dict) or self.user is None:
            return
        edit_id = data.get("id")
        if not edit_id:
            return
        from .prompt import _session_settings  # pylint: disable=import-outside-toplevel

        pending = _session_settings.get(self.user.pk, {}).get("pending_edits", {})
        pending.pop(edit_id, None)

    def _on_mssp_request(self) -> dict:
        from django.conf import settings as django_settings  # pylint: disable=import-outside-toplevel
        from moo import __version__  # pylint: disable=import-outside-toplevel

        players_online = str(len(_active_sessions))
        return {
            "NAME": getattr(django_settings, "MOO_NAME", "DjangoMOO"),
            "CODEBASE": "DjangoMOO",
            "VERSION": __version__,
            "PLAYERS": players_online,
            "UPTIME": str(_total_connections),
            "FAMILY": "Custom",
            "GENRE": "None",
            "LANGUAGE": "English",
            "CHARSET": "UTF-8",
            "SSL": "0",
        }


@sync_to_async
def _available_sites_for_user(user) -> tuple[list, bool]:
    """Return ``(sites, is_universal_wizard)`` for picker display.

    Non-wizards see only Sites where they already have a Player.  Universal
    wizards see every Site in the database, since their whole point is
    cross-universe access (auto-provision on first connect to a new site).
    """
    from django.contrib.sites.models import Site

    from moo.core.models.auth import Player, UniversalWizard

    is_universal = UniversalWizard.objects.filter(user=user).exists()
    if is_universal:
        return list(Site.objects.order_by("domain")), True
    site_ids = Player.objects.filter(user=user).values_list("site_id", flat=True).distinct()
    return list(Site.objects.filter(pk__in=list(site_ids)).order_by("domain")), False


async def _pick_site(session: "MooPromptToolkitSSHSession", user) -> "object | None":
    """Resolve a Site for *user* when the username carried no suffix.

    Auto-picks when there is exactly one available Site; prompts otherwise.
    Returns ``None`` when the user has no available Sites, in which case
    :func:`interact` should disconnect.
    """
    from prompt_toolkit.shortcuts.prompt import PromptSession

    sites, _is_universal = await _available_sites_for_user(user)
    if not sites:
        return None

    if len(sites) == 1:
        return sites[0]

    chan = getattr(session, "_chan", None)
    if chan is None:
        return sites[0]

    chan.write("\r\nAvailable universes:\r\n")
    for idx, s in enumerate(sites, 1):
        chan.write(f"  [{idx}] {s.domain}\r\n")
    chan.write(
        f"\r\nTip: skip this prompt next time with ``ssh {user.username}{USER_SITE_DELIMITER}<domain>@…``.\r\n\r\n"
    )

    prompt_session: PromptSession = PromptSession()
    while True:
        try:
            answer = await prompt_session.prompt_async(f"Pick a universe [1-{len(sites)}]: ")
        except (EOFError, KeyboardInterrupt):
            return None
        answer = (answer or "").strip()
        if not answer:
            continue
        try:
            choice = int(answer)
        except ValueError:
            chan.write("Please enter a number.\r\n")
            continue
        if 1 <= choice <= len(sites):
            return sites[choice - 1]
        chan.write(f"Choice must be between 1 and {len(sites)}.\r\n")


async def interact(ssh_session: PromptToolkitSSHSession) -> None:
    """
    Initial entry point for SSH sessions.

    :param ssh_session: the session being started
    """
    global _total_connections  # pylint: disable=global-statement
    session = cast(MooPromptToolkitSSHSession, ssh_session)
    mode = getattr(session, "mode", "rich")
    username = session.user.username if session.user else "unknown"
    _active_sessions.add(username)
    _total_connections += 1
    log.info(
        "connect user=%s total=%d active=%d fds=%d mode=%s",
        username,
        _total_connections,
        len(_active_sessions),
        _fd_count(),
        mode,
    )

    try:
        if session.site is None and session.user is not None:
            site = await _pick_site(session, session.user)
            if site is None:
                chan = getattr(session, "_chan", None)
                if chan is not None:
                    chan.write("\r\nNo accessible universe for this account.\r\n")
                return
            session.site = site
            await sync_to_async(_provision_after_pick)(session.user, site)

        chan = getattr(session, "_chan", None)
        if chan is not None and session.site is not None:
            chan.write(f"\r\nConnected to universe: {session.site.domain}\r\n\r\n")

        await embed(session.user, session=session, mode=mode, site=getattr(session, "site", None))
    finally:
        _active_sessions.discard(username)
        log.info("disconnect user=%s active=%d fds=%d", username, len(_active_sessions), _fd_count())


def _provision_after_pick(user, site) -> None:
    """Provision a UniversalWizard's Player+avatar on a freshly-picked Site.

    Mirrors :meth:`SSHServer._auto_provision_universal_wizard` for the picker
    branch where ``self.site`` was unknown at auth time.  Idempotent.
    """
    from moo.core.models.auth import Player, UniversalWizard
    from moo.core.models.object import Object

    if not UniversalWizard.objects.filter(user=user).exists():
        return
    if Player.objects.filter(user=user, site=site).exists():
        return
    avatar = _provision_wizard_avatar(user, site)
    Player.objects.create(user=user, avatar=avatar, wizard=True, site=site)


def _provision_wizard_avatar(user, site):
    """Create or fetch a wizard avatar named after ``user.username`` on ``site``,
    properly parented to ``Generic Wizard`` and located at ``$player_start``.

    The avatar name is the username (not ``"Wizard"``) so it stays unique
    within the site alongside the bootstrap Wizard. Idempotent.
    """
    from moo.core.exceptions import NoSuchPropertyError
    from moo.core.models.object import Object

    avatar, created = Object.global_objects.get_or_create(
        name=user.username,
        unique_name=True,
        site=site,
    )
    if not created and avatar.parents.exists() and avatar.location_id is not None:
        return avatar  # already fully provisioned
    if created:
        avatar.owner = avatar
        avatar.save()
    if not avatar.parents.exists():
        generic_wizard = Object.global_objects.filter(site=site, name="Generic Wizard", unique_name=True).first()
        if generic_wizard is not None:
            avatar.parents.add(generic_wizard)
    if avatar.location_id is None:
        system = Object.global_objects.filter(site=site, name="System Object", unique_name=True).first()
        if system is not None:
            try:
                start = system.get_property("player_start")
            except NoSuchPropertyError:
                start = None
            if start is not None:
                avatar.location = start
                avatar.save()
    return avatar


async def _health_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.write(b"OK\n")
    await writer.drain()
    writer.close()


async def server(port=8022):
    """
    Create an AsyncSSH server on the requested port.

    :param port: the port to run the SSH daemon on.
    """
    await asyncio.sleep(1)

    loop = asyncio.get_event_loop()

    # faulthandler dumps thread stacks synchronously, even when the event loop
    # is blocked — unlike loop.add_signal_handler which needs a live loop.
    faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True, chain=False)

    def _dump_state():
        tasks = asyncio.all_tasks()
        log.critical("SIGUSR2 state dump: sessions=%s tasks=%d fds=%d", _active_sessions, len(tasks), _fd_count())
        for t in tasks:
            log.critical("  TASK: %s", t)

    loop.add_signal_handler(signal.SIGUSR2, _dump_state)

    await asyncio.start_server(_health_handler, "", 8023)
    log.info("Health endpoint listening on port 8023")

    await asyncssh.create_server(
        lambda: SSHServer(interact),
        "",
        port,
        server_host_keys=["/etc/ssh/ssh_host_ecdsa_key"],
        kex_algs=[
            "mlkem768x25519-sha256",
            "sntrup761x25519-sha512@openssh.com",
            "curve25519-sha256",
            "ecdh-sha2-nistp256",
            "diffie-hellman-group14-sha256",
        ],
        line_editor=False,
        keepalive_interval=15,
        keepalive_count_max=3,
    )
    await asyncio.Future()


class SSHServer(PromptToolkitSSHServer):
    """
    Create an SSH server for client access.
    """

    user = None
    site = None

    def begin_auth(self, _: str) -> bool:
        """
        Allow user login.
        """
        return True

    def password_auth_supported(self) -> bool:
        """
        Allow password authentication.
        """
        return True

    def _resolve_site(self):
        """Resolve the active Site for this connection.

        Order of precedence:

        1. ``self._site_hint`` — the suffix parsed from the SSH username
           (``user+sitedomain``).  This is the only path that actually carries
           the dialed hostname through SSH; webssh injects it server-side from
           the browser ``Host`` header before forwarding.
        2. Leave ``self.site = None`` so :func:`interact` runs the post-auth
           picker.

        ``conn.get_extra_info("server_host")`` is intentionally not consulted:
        it returns the local bind interface, not the hostname the client
        dialed.
        """
        from django.contrib.sites.models import Site

        hint = getattr(self, "_site_hint", None)
        if hint:
            self.site = Site.objects.filter(domain=hint).first()
            if self.site:
                return
            log.warning("SSH username site suffix %s is unknown — deferring to picker", hint)
        self.site = None

    def _login_block_reason(self):
        """Return a sanction reason blocking this login, or ``None`` (spec 200, H).

        Consulted by both auth paths once ``self.user``/``self.site`` are known.
        With a resolved site we check that one account; without (picker
        deferred) we block if *any* of the user's accounts is sanctioned.
        """
        from moo.core.models.auth import Player
        from moo.sdk.moderation import account_login_blocked

        if not self.user:
            return None
        accounts = Player.objects.filter(user=self.user)
        if self.site is not None:
            accounts = accounts.filter(site=self.site)
        for account in accounts:
            reason = account_login_blocked(account)
            if reason:
                return reason
        return None

    def _auto_provision_universal_wizard(self):
        """Provision a wizard avatar+Player for a UniversalWizard user on a new site."""
        from moo.core.models.auth import Player, UniversalWizard

        if not (self.user and self.site):
            return
        if not UniversalWizard.objects.filter(user=self.user).exists():
            return
        # Idempotent: a Player for this (user, site) already exists.
        if Player.objects.filter(user=self.user, site=self.site).exists():
            return
        avatar = _provision_wizard_avatar(self.user, self.site)
        Player.objects.create(user=self.user, avatar=avatar, wizard=True, site=self.site)

    @sync_to_async
    def validate_password(self, username: str, password: str) -> bool:
        """
        Validate a password login.

        :param username: username of the Django User to login as
        :param password: the password string
        """
        base_username, site_hint = _split_user_suffix(username)
        try:
            user = User.objects.get(username=base_username)
        except User.DoesNotExist:
            return False
        if user.check_password(password):
            self.user = user  # pylint: disable=attribute-defined-outside-init
            self._site_hint = site_hint  # pylint: disable=attribute-defined-outside-init
            self._resolve_site()
            self._auto_provision_universal_wizard()
            reason = self._login_block_reason()
            if reason:
                log.warning("Denying login for %s: %s", base_username, reason)
                return False
            return True
        return False

    def public_key_auth_supported(self) -> bool:
        """
        Allow public key authentication.
        """
        return True

    @sync_to_async
    def validate_public_key(self, username: str, key: asyncssh.SSHKey):
        """
        Validate a public key login.

        :param username: username of the Django User to login as
        :param key: the SSH key
        """
        base_username, site_hint = _split_user_suffix(username)
        for user_key in UserKey.objects.filter(user__username=base_username).select_related("user"):
            user_pem = " ".join(user_key.key.split()[:2]) + "\n"
            server_pem = key.export_public_key().decode("utf8")
            if user_pem == server_pem:
                self.user = user_key.user  # pylint: disable=attribute-defined-outside-init
                self._site_hint = site_hint  # pylint: disable=attribute-defined-outside-init
                self._resolve_site()
                self._auto_provision_universal_wizard()
                reason = self._login_block_reason()
                if reason:
                    log.warning("Denying key login for %s: %s", base_username, reason)
                    return False
                return True
        return False

    def session_requested(self) -> PromptToolkitSSHSession:
        """
        Setup a session and associate the Django User object.
        """
        session = MooPromptToolkitSSHSession(self.interact, enable_cpr=self.enable_cpr)
        session.user = self.user
        session.site = getattr(self, "site", None)
        return session
