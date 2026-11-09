"""Pinned PyMax over a synthetic WebSocket; no MAX, Postgres or Redis access.

The socket boundary is the only replaced transport layer: real WebSocketTransport,
WSReader, TcpProtocol, ConnectionManager, App, SessionStore and QrAuthFlow run.
Replies use PyMax's binary msgpack framing and echo request opcode/sequence.
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import asdict, fields
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import ssl
import stat
import sys
import time
from uuid import UUID

import pytest
from pymax.auth.exceptions import PasswordAttemptsExceededError
from pymax.auth.qr import QrAuthFlow
from pymax.protocol import Command, OutboundFrame
from pymax.protocol.enums import Opcode
from pymax.protocol.tcp import TcpProtocol
from pymax.session import SessionStore
from pymax.session.models import SessionInfo
from pymax.transport.websocket import WebSocketTransport
from websockets.asyncio import client as websocket_client

from catix.maxuserbot.client import AccountClient, LoginRequired, ProtocolError, SessionBusy, SessionLock
from catix.maxuserbot.models import MessageSnapshot, PhotoRef, db_chat_id, normalize_id, normalize_message, normalize_event

ACCOUNT_ID = 4242
TOKEN = "synthetic-login-token-NEVER-LOG"
QR_LINK = "https://max.ru/qr?token=synthetic-QR-secret"
TRACK_ID = "synthetic-track-secret"
PASSWORD = "synthetic-2FA-password-NEVER-LOG"
SECRET_TEXT = "synthetic-private-message-NEVER-LOG"
DEVICE_ID = "3cf9ff2a-9f08-4d51-8f4f-f555e94a9999"
NOW_MS = 1_800_000_000_000


def chat(raw_id=101, kind="CHAT", **extra):
    return {"id": raw_id, "type": kind, "status": "ACTIVE", "owner": ACCOUNT_ID,
            "title": f"Source {raw_id}", **extra}


def message(message_id=7, **extra):
    return {"id": message_id, "chatId": 101, "time": NOW_MS, "sender": 88,
            "text": "Original caption", "attaches": [], **extra}


class SyntheticSocket:
    """Minimal websockets ClientConnection surface, with the real binary codec."""

    def __init__(self, wire):
        self.wire = wire
        self.incoming = asyncio.Queue()
        self.close_code = None
        self.closed = False

    async def send(self, data):
        assert isinstance(data, bytes), "exercise real TcpProtocol encoding"
        frame = self.wire.codec.decode(data)
        self.wire.requests.append(frame)
        opcode = frame.opcode
        if self.wire.replies[opcode]:
            cmd, payload = self.wire.replies[opcode].popleft()
        elif opcode == Opcode.SESSION_INIT:
            cmd, payload = Command.RESPONSE, {"callsSeed": 1}
        elif opcode == Opcode.PING:
            cmd, payload = Command.RESPONSE, {}
        elif opcode == Opcode.LOGIN:
            cmd, payload = Command.RESPONSE, {
                "profile": {"contact": {"id": ACCOUNT_ID}},
                "chats": [chat(), chat(102, "CHANNEL"), chat(103, "DIALOG")],
                "contacts": [], "messages": {},
            }
        else:
            raise AssertionError(f"Unscripted outbound opcode: {opcode}")
        response = OutboundFrame(ver=10, opcode=opcode, seq=frame.seq,
                                 cmd=cmd, payload=payload)
        self.incoming.put_nowait(self.wire.codec.encode(response))

    async def recv(self, decode=False):
        assert decode is False
        return await self.incoming.get()

    async def close(self):
        self.close_code = 1000
        self.closed = True

    async def wait_closed(self):
        assert self.closed


class Wire:
    def __init__(self):
        self.codec = TcpProtocol()
        self.replies = defaultdict(deque)
        self.requests = []
        self.connections = []
        self.sockets = []
        self.connect_error = None

    def reply(self, opcode, payload, *, cmd=Command.RESPONSE):
        self.replies[opcode].append((cmd, payload))

    async def connect(self, url, **kwargs):
        # Keeping upstream WebSocketTransport also keeps its normal verified TLS.
        assert url.startswith("wss://")
        assert kwargs.get("ssl") is not False
        context = kwargs.get("ssl")
        if isinstance(context, ssl.SSLContext):
            assert context.verify_mode == ssl.CERT_REQUIRED
            assert context.check_hostname
        self.connections.append((url, kwargs))
        if self.connect_error is not None:
            raise self.connect_error
        socket = SyntheticSocket(self)
        self.sockets.append(socket)
        return socket

    def sent(self, opcode):
        return [frame.payload for frame in self.requests if frame.opcode == opcode]

    def qr(self, *, expired=False, password=False):
        expires = 0 if expired else int(time.time() * 1000) + 60_000
        self.reply(Opcode.GET_QR, {"expiresAt": expires, "pollingInterval": 0,
                                  "qrLink": QR_LINK, "trackId": TRACK_ID, "ttl": 60_000})
        if not expired:
            self.reply(Opcode.GET_QR_STATUS, {"status": {"expiresAt": expires, "loginAvailable": True}})
            confirmation = ({"passwordChallenge": {"trackId": TRACK_ID, "hint": "private hint"}}
                            if password else {"tokenAttrs": {"LOGIN": {"token": TOKEN}}})
            self.reply(Opcode.LOGIN_BY_QR, confirmation)


@pytest.fixture(autouse=True)
def restore_transport_logging():
    """AccountClient intentionally suppresses library logs; don't leak this to other tests."""
    names = ("pymax", "websockets", "aiosqlite")
    saved = {}
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(logger, logging.Logger) and any(name == root or name.startswith(root + ".") for root in names):
            saved[name] = (logger.level, logger.handlers[:], logger.filters[:], logger.propagate, logger.disabled)
    yield
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if not isinstance(logger, logging.Logger):
            continue
        if name in saved:
            level, handlers, filters, propagate, disabled = saved[name]
            logger.setLevel(level)
            logger.handlers[:] = handlers
            logger.filters[:] = filters
            logger.propagate = propagate
            logger.disabled = disabled
        elif any(name == root or name.startswith(root + ".") for root in names):
            logger.handlers.clear()
            logger.filters.clear()
            logger.setLevel(logging.NOTSET)
            logger.propagate = True
            logger.disabled = False


@pytest.fixture
def wire(monkeypatch):
    wire = Wire()
    monkeypatch.setattr(websocket_client, "connect", wire.connect)
    return wire


async def save_session(path, token=TOKEN):
    store = SessionStore(str(path.parent), path.name)
    try:
        await store.save_session(SessionInfo(token=token, device_id=DEVICE_ID, phone=""))
    finally:
        await store.close()


async def load_session(path):
    store = SessionStore(str(path.parent), path.name)
    try:
        return await store.load_session()
    finally:
        await store.close()


class Providers:
    def __init__(self):
        self.qrs = []
        self.hints = []

    async def show_qr(self, url):
        self.qrs.append(url)

    async def get_password(self, hint=None):
        self.hints.append(hint)
        return PASSWORD


def assert_no_secrets(text):
    for secret in (TOKEN, QR_LINK, TRACK_ID, PASSWORD, SECRET_TEXT, DEVICE_ID):
        assert secret not in text


def assert_read_only(wire):
    permitted = {Opcode.SESSION_INIT, Opcode.PING, Opcode.LOGIN, Opcode.CHATS_LIST,
                 Opcode.CHAT_INFO, Opcode.CHAT_HISTORY, Opcode.MSG_GET,
                 Opcode.GET_QR, Opcode.GET_QR_STATUS, Opcode.LOGIN_BY_QR,
                 Opcode.AUTH_LOGIN_CHECK_PASSWORD}
    assert {frame.opcode for frame in wire.requests} <= permitted
    for opcode in (Opcode.LOGIN, Opcode.PING):
        assert all(payload["interactive"] is False for payload in wire.sent(opcode))


@pytest.mark.parametrize("empty_sqlite", [False, True])
def test_missing_session_refuses_authentication_before_transport(tmp_path, wire, empty_sqlite):
    path = tmp_path / "account.db"

    async def scenario():
        if empty_sqlite:
            assert await load_session(path) is None
        client = AccountClient(path)
        try:
            with pytest.raises(LoginRequired, match="login_required"):
                await client.connect()
        finally:
            await client.close()

    asyncio.run(scenario())
    assert not wire.connections
    assert not wire.requests


def test_saved_sqlite_session_logs_in_without_qr_or_password(tmp_path, wire):
    path = tmp_path / "account.db"
    providers = Providers()

    async def scenario():
        await save_session(path)
        # Explicit login verifies a valid existing session; it must not switch accounts.
        client = AccountClient(path, login=True, qr_provider=providers, password_provider=providers)
        try:
            await client.connect()
            assert client.account_id == ACCOUNT_ID
            assert [item["raw_chat_id"] for item in client.login_chats] == [101, 102]
            assert [item["kind"] for item in client.login_chats] == ["chat", "channel"]
            assert isinstance(client._client._connection.transport, WebSocketTransport)
        finally:
            await client.close()
        assert (await load_session(path)).token == TOKEN

    asyncio.run(scenario())
    assert providers.qrs == providers.hints == []
    assert wire.sent(Opcode.LOGIN)[0]["token"] == TOKEN
    assert len(wire.connections) == 1
    assert all(socket.closed for socket in wire.sockets)
    assert_read_only(wire)


def test_revoked_session_never_falls_back_to_qr_or_erases_sqlite(tmp_path, wire, caplog):
    path = tmp_path / "account.db"
    wire.reply(Opcode.LOGIN, {"error": "FAIL_LOGIN_TOKEN", "message": TOKEN}, cmd=Command.ERROR)

    async def scenario():
        await save_session(path)
        caplog.clear()  # Fixture creation is not application-owned logging.
        client = AccountClient(path)
        try:
            with pytest.raises(LoginRequired):
                await client.connect()
        finally:
            await client.close()
        assert (await load_session(path)).token == TOKEN

    with caplog.at_level(logging.DEBUG, logger="pymax"):
        asyncio.run(scenario())
    assert not wire.sent(Opcode.GET_QR)
    assert not wire.sent(Opcode.AUTH)
    assert len(wire.connections) == 1
    assert_no_secrets(caplog.text)


def test_catalog_pages_keep_marker_and_drop_private_bodies(tmp_path, wire):
    wire.reply(Opcode.CHATS_LIST, {"chats": [chat(lastMessage=message(text=SECRET_TEXT),
                                                pinnedMessage=message(text=SECRET_TEXT)),
                                            chat(102, "CHANNEL"), chat(103, "DIALOG")], "marker": 700})
    wire.reply(Opcode.CHATS_LIST, {"chats": [chat(104, "DIALOG")], "marker": 600})
    wire.reply(Opcode.CHATS_LIST, {"chats": [], "marker": 500})

    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        client = AccountClient(path)
        try:
            await client.connect()
            chats, marker = await client.catalog_page(800)
            assert marker == 700
            assert chats == [{"raw_chat_id": 101, "kind": "chat", "title": "Source 101", "status": "ACTIVE", "link": None},
                             {"raw_chat_id": 102, "kind": "channel", "title": "Source 102", "status": "ACTIVE", "link": None}]
            assert SECRET_TEXT not in repr(chats)
            assert await client.catalog_page(marker) == ([], 600)
            assert await client.catalog_page(600) == ([], None)
        finally:
            await client.close()

    asyncio.run(scenario())
    assert wire.sent(Opcode.CHATS_LIST) == [{"marker": 800}, {"marker": 700}, {"marker": 600}]
    assert_read_only(wire)


@pytest.mark.parametrize("payload,code", [
    ({}, "protocol_error"),
    ({"chats": None, "marker": 0}, "protocol_error"),
    ({"chats": [chat()]}, "catalog_pagination_unknown"),
    ({"chats": [chat()], "marker": True}, "protocol_error"),
    ({"chats": [chat()], "marker": 1.5}, "protocol_error"),
    ({"chats": [chat()], "marker": 2**63}, "protocol_error"),
    ({"chats": [chat(kind="UNRECOGNIZED")], "marker": 0}, "protocol_error"),
])
def test_malformed_catalog_is_not_a_complete_catalog(tmp_path, wire, payload, code):
    wire.reply(Opcode.CHATS_LIST, payload)

    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        client = AccountClient(path)
        try:
            await client.connect()
            with pytest.raises(ProtocolError) as raised:
                await client.catalog_page(NOW_MS)
            assert raised.value.code == code
        finally:
            await client.close()

    asyncio.run(scenario())


def test_chat_info_is_fresh_not_login_cache(tmp_path, wire):
    wire.reply(Opcode.CHAT_INFO, {"chats": [chat(title="Fresh title")]})
    wire.reply(Opcode.CHAT_INFO, {"chats": []})

    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        client = AccountClient(path)
        try:
            await client.connect()
            assert (await client.chat(101))["title"] == "Fresh title"
            assert await client.chat(101) == {}
        finally:
            await client.close()

    asyncio.run(scenario())
    assert wire.sent(Opcode.CHAT_INFO) == [{"chatIds": [101]}, {"chatIds": [101]}]


def test_history_zero_cursor_and_two_year_old_message_use_exact_raw_payload(tmp_path, wire):
    old = message(time=NOW_MS - 730 * 86_400_000)
    old.pop("chatId")  # MAX history may omit the chat ID; the caller supplies it.
    wire.reply(Opcode.CHAT_HISTORY, {"messages": [old]})
    wire.reply(Opcode.CHAT_HISTORY, {"messages": []})

    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        client = AccountClient(path)
        try:
            await client.connect()
            raw = await client.history(101, NOW_MS + 1)
            assert normalize_message(raw[0], 101).created_ms == old["time"]
            assert await client.history(101, 0) == []
        finally:
            await client.close()

    asyncio.run(scenario())
    expected = {"chatId": 101, "backward": 100, "forward": 0, "backwardTime": 0,
                "forwardTime": 0, "getMessages": True, "getChat": False,
                "itemType": "REGULAR", "interactive": False}
    assert wire.sent(Opcode.CHAT_HISTORY) == [{**expected, "from": NOW_MS + 1}, {**expected, "from": 0}]
    assert_read_only(wire)


@pytest.mark.parametrize("payload", [
    {}, {"messages": None}, {"messages": {}}, {"messages": [None]},
    {"messages": [message(id=True)]}, {"messages": [message(time=-1)]},
    {"messages": [message(time=NOW_MS + 1)]}, {"messages": [message(chatId=102)]},
    {"messages": [message(id="opaque-mid")]}, {"messages": [message(id=2**63)]},
    {"messages": [message(time=True)]}, {"messages": [message(attaches=None)]},
])
def test_malformed_history_never_means_end_of_archive(tmp_path, wire, payload):
    wire.reply(Opcode.CHAT_HISTORY, payload)

    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        client = AccountClient(path)
        try:
            await client.connect()
            with pytest.raises(ProtocolError):
                await client.history(101, NOW_MS)
        finally:
            await client.close()

    asyncio.run(scenario())


def test_message_refetch_retains_native_int64_ids_and_explicit_removal(tmp_path, wire):
    native_id = 2**63 - 1
    wire.reply(Opcode.MSG_GET, {"messages": [message(native_id), {"id": 8, "status": "REMOVED"}]})
    wire.reply(Opcode.MSG_GET, {"messages": []})
    wire.reply(Opcode.MSG_GET, {"messages": [message(99)]})

    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        client = AccountClient(path)
        try:
            await client.connect()
            fetched = await client.messages(101, [native_id, 8])
            assert normalize_message(fetched[0], 101).message_id == native_id
            assert normalize_message(fetched[1], 101).deleted
            assert await client.messages(101, [9]) == []
            with pytest.raises(ProtocolError):
                await client.messages(101, [7])
        finally:
            await client.close()

    asyncio.run(scenario())
    assert wire.sent(Opcode.MSG_GET) == [{"chatId": 101, "messageIds": [native_id, 8]},
                                        {"chatId": 101, "messageIds": [9]},
                                        {"chatId": 101, "messageIds": [7]}]
    assert_read_only(wire)


@pytest.mark.parametrize("password", [False, True])
def test_real_qr_flow_uses_providers_and_persists_session(tmp_path, wire, caplog, password):
    providers = Providers()
    wire.qr(password=password)
    if password:
        wire.reply(Opcode.AUTH_LOGIN_CHECK_PASSWORD, {"tokenAttrs": {"LOGIN": {"token": TOKEN}}})
    path = tmp_path / "account.db"

    async def scenario():
        client = AccountClient(path, login=True, qr_provider=providers, password_provider=providers)
        assert isinstance(client._client._auth_flow, QrAuthFlow)
        try:
            await client.connect()
            assert client.account_id == ACCOUNT_ID
        finally:
            await client.close()
        assert (await load_session(path)).token == TOKEN
        # The next daemon start uses SQLite, not another QR challenge.
        daemon = AccountClient(path)
        try:
            await daemon.connect()
            assert daemon.account_id == ACCOUNT_ID
        finally:
            await daemon.close()

    with caplog.at_level(logging.DEBUG, logger="pymax"):
        asyncio.run(scenario())
    assert providers.qrs == [QR_LINK]
    assert providers.hints == (["private hint"] if password else [])
    assert len(wire.sent(Opcode.GET_QR)) == 1
    if password:
        assert wire.sent(Opcode.AUTH_LOGIN_CHECK_PASSWORD) == [{"trackId": TRACK_ID, "password": PASSWORD}]
    assert_no_secrets(caplog.text)
    assert_read_only(wire)


def test_qr_expiry_does_not_save_session_or_report_success(tmp_path, wire, caplog):
    providers = Providers()
    wire.qr(expired=True)
    path = tmp_path / "account.db"

    async def scenario():
        client = AccountClient(path, login=True, qr_provider=providers, password_provider=providers)
        try:
            with pytest.raises(RuntimeError, match="expired"):
                await client.connect()
        finally:
            await client.close()
        assert await load_session(path) is None

    with caplog.at_level(logging.DEBUG, logger="pymax"):
        asyncio.run(scenario())
    assert providers.qrs == [QR_LINK]
    assert providers.hints == []
    assert not wire.sent(Opcode.LOGIN_BY_QR)
    assert not wire.sent(Opcode.LOGIN)
    assert all(socket.closed for socket in wire.sockets)
    assert_no_secrets(caplog.text)


def test_real_qr_two_factor_stops_after_three_failed_passwords(tmp_path, wire, caplog):
    providers = Providers()
    wire.qr(password=True)
    for _ in range(3):
        wire.reply(Opcode.AUTH_LOGIN_CHECK_PASSWORD, {"error": PASSWORD})
    path = tmp_path / "account.db"

    async def scenario():
        client = AccountClient(path, login=True, qr_provider=providers, password_provider=providers)
        try:
            with pytest.raises(PasswordAttemptsExceededError):
                await client.connect()
        finally:
            await client.close()
        assert await load_session(path) is None

    with caplog.at_level(logging.DEBUG, logger="pymax"):
        asyncio.run(scenario())
    assert len(providers.hints) == 3
    assert len(wire.sent(Opcode.AUTH_LOGIN_CHECK_PASSWORD)) == 3
    assert not wire.sent(Opcode.LOGIN)
    assert_no_secrets(caplog.text)


def test_untrusted_tls_fails_without_insecure_retry(tmp_path, wire, caplog):
    wire.connect_error = ssl.SSLCertVerificationError("synthetic untrusted certificate " + TOKEN)

    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        caplog.clear()  # Fixture creation is not application-owned logging.
        client = AccountClient(path)
        try:
            with pytest.raises((ConnectionError, ssl.SSLCertVerificationError)):
                await client.connect()
        finally:
            await client.close()

    with caplog.at_level(logging.DEBUG, logger="pymax"):
        asyncio.run(scenario())
    assert len(wire.connections) == 1
    assert not wire.requests
    assert_no_secrets(caplog.text)


@pytest.mark.parametrize("value,expected", [
    (-(2**63), -(2**63)), (2**63 - 1, 2**63 - 1), (0, 0),
    (str(-(2**63)), -(2**63)), (str(2**63 - 1), 2**63 - 1), ("0007", 7), ("-7", -7),
])
def test_explicit_id_normalization_preserves_int64(value, expected):
    result = normalize_id(value)
    assert type(result) is int
    assert result == expected


@pytest.mark.parametrize("value", [
    True, False, None, 1.0, -1.5, float("nan"), float("inf"),
    2**63, -(2**63) - 1, str(2**63), str(-(2**63) - 1),
    "", " 7", "7 ", "+7", "1.0", "1e3", "0x10", "opaque-mid", "１２", "١٢", b"7", [], {},
])
def test_ids_never_accept_bool_float_opaque_or_non_ascii(value):
    with pytest.raises(ProtocolError):
        normalize_id(value)


@pytest.mark.parametrize("raw_id", [-10**13 + 1, -101, 0, 101, 10**13 - 1])
def test_user_account_namespace_is_distinct_from_legacy(raw_id):
    assert db_chat_id(raw_id) == 4 * 10**15 + raw_id
    assert db_chat_id(raw_id) != 2 * 10**15 + raw_id


@pytest.mark.parametrize("raw_id", [-10**13, 10**13, -(2**63), 2**63 - 1])
def test_chat_identity_range_is_explicit(raw_id):
    with pytest.raises(ProtocolError) as raised:
        db_chat_id(raw_id)
    assert raised.value.code == "identity_range"


def test_message_snapshot_keeps_only_stable_photo_identity():
    raw = message("9223372036854775807", sender="88", link={"type": "REPLY", "message": {"id": "6"}},
                  attaches=[{"_type": "PHOTO", "photoId": "91", "baseUrl": QR_LINK, "photoToken": TOKEN},
                            {"_type": "STICKER", "photoId": 92}, {"_type": "VIDEO", "photoId": 93}])
    snapshot = normalize_message(raw, 101)
    assert isinstance(snapshot, MessageSnapshot)
    assert {field.name for field in fields(snapshot)} == {
        "raw_chat_id", "message_id", "created_ms", "text", "sender_id", "sender_name",
        "reply_to", "photos", "deleted"}
    assert snapshot.message_id == 2**63 - 1
    assert snapshot.created_ms == NOW_MS
    assert snapshot.sender_id == 88
    assert snapshot.reply_to == 6
    assert snapshot.photos == (PhotoRef(photo_id=91),)
    assert snapshot.deleted is False
    assert_no_secrets(repr(asdict(snapshot)))


def test_comments_are_excluded_and_removed_messages_need_no_creation_time():
    assert normalize_message(message(postId=45), 101) is None
    deleted = normalize_message({"id": 7, "status": "REMOVED"}, 101)
    assert deleted.deleted
    assert deleted.message_id == 7
    assert deleted.raw_chat_id == 101
    assert deleted.photos == ()


@pytest.mark.parametrize("extra", [
    {"id": True}, {"time": None}, {"time": -1}, {"chatId": 102},
    {"sender": False}, {"text": None}, {"attaches": [None]},
    {"attaches": [{"_type": "PHOTO", "photoId": True}]},
    {"attaches": [{"_type": "PHOTO", "photoId": 2**63}]},
    {"link": {"type": "REPLY", "message": {"id": "opaque-mid"}}},
])
def test_malformed_message_fields_are_not_silently_coerced(extra):
    with pytest.raises(ProtocolError):
        normalize_message(message(**extra), 101)


def test_session_lock_is_exclusive_and_releases_after_error(tmp_path):
    path = tmp_path / "private" / "account.db"
    with SessionLock(path):
        with pytest.raises(SessionBusy):
            with SessionLock(path):
                pytest.fail("independent file descriptor must not take the same flock")
        with pytest.raises(SessionBusy):
            with SessionLock(path):
                pass
    with pytest.raises(RuntimeError):
        with SessionLock(path):
            raise RuntimeError("synthetic cancellation")
    with SessionLock(path):
        pass


def test_lock_covers_sqlite_and_sidecar_permissions_and_restores_umask(tmp_path):
    path = tmp_path / "private" / "account.db"
    previous = os.umask(0o022)
    try:
        with SessionLock(path):
            asyncio.run(save_session(path))
            for suffix in ("-journal", "-wal", "-shm"):
                Path(str(path) + suffix).touch()
            with pytest.raises(SessionBusy):
                with SessionLock(path):
                    pass
            # Failed lock acquisition must restore the outer lock's private umask.
            proof = path.parent / "private-proof"
            proof.touch()
            assert stat.S_IMODE(proof.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        for suffix in ("", "-journal", "-wal", "-shm", ".lock"):
            assert stat.S_IMODE(Path(str(path) + suffix).stat().st_mode) == 0o600
        observed = os.umask(0o022)
        assert observed == 0o022
    finally:
        os.umask(previous)


def test_cli_help_exits_before_network_database_or_settings(monkeypatch, capsys, wire):
    from catix.maxuserbot import userbot

    def forbidden(*args, **kwargs):
        pytest.fail("--help must not initialize account or database resources")

    from catix.db import pg
    monkeypatch.setattr(AccountClient, "__init__", forbidden)
    monkeypatch.setattr(pg, "connection", forbidden)
    monkeypatch.setattr(userbot, "_execute", forbidden)
    monkeypatch.setattr(sys, "argv", ["catix-maxuserbot", "--help"])
    with pytest.raises(SystemExit) as raised:
        userbot.main()
    assert raised.value.code == 0
    output = capsys.readouterr()
    assert "login" in output.out and "chats" in output.out and "listen" in output.out
    assert not wire.connections


def test_cli_login_without_terminal_never_connects(monkeypatch, capsys, wire):
    from catix.maxuserbot import userbot

    monkeypatch.setattr(sys, "argv", ["catix-maxuserbot", "login"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit) as raised:
        userbot.main()
    assert raised.value.code != 0
    assert "login_requires_tty" in capsys.readouterr().err
    assert not wire.connections


def test_cli_qr_expiry_has_nonzero_exit_and_no_success(tmp_path, monkeypatch, capsys, wire):
    from catix.maxuserbot import userbot
    from catix.settings import settings

    wire.qr(expired=True)
    monkeypatch.setattr(settings, "max_session", tmp_path / "private" / "account.db")
    monkeypatch.setattr(sys, "argv", ["catix-maxuserbot", "login"])
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    with pytest.raises(SystemExit) as raised:
        userbot.main()
    assert raised.value.code != 0
    output = capsys.readouterr()
    assert "successful" not in output.out.lower()
    assert "login_failed" in output.err
    assert_no_secrets(output.out + output.err)
    assert not wire.sent(Opcode.LOGIN)


def inject_frame(wire, opcode, payload, *, cmd=Command.REQUEST, seq=60000):
    frame = OutboundFrame(ver=10, opcode=opcode, seq=seq, cmd=cmd, payload=payload)
    wire.sockets[-1].incoming.put_nowait(wire.codec.encode(frame))


def test_receive_hook_serializes_admission_and_uses_connection_uuid_ordinals(tmp_path, wire):
    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        seen = []
        entered, release, completed = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def sink(opcode, payload, observed_at, key):
            seen.append((opcode, payload, observed_at, key))
            if len(seen) == 1:
                entered.set()
                await release.wait()
            if len(seen) == 3:
                completed.set()

        prefixes = []
        for connection_number in range(2):
            client = AccountClient(path)
            admitted_before_connect = len(seen)
            try:
                await client.connect()
                assert len(seen) == admitted_before_connect
                client.sink = sink
                lower = datetime.now(timezone.utc)
                if connection_number == 0:
                    inject_frame(wire, 128, message(text="A"))
                    await asyncio.wait_for(entered.wait(), 2)
                    inject_frame(wire, 67, message(text="B"))
                    inject_frame(wire, 67, message(text="A"))
                    await asyncio.sleep(0)
                    assert len(seen) == 1, "later frames must not overtake uncommitted admission"
                    release.set()
                    await asyncio.wait_for(completed.wait(), 2)
                    batch = seen[:]
                    assert [row[1]["text"] for row in batch] == ["A", "B", "A"]
                else:
                    completed.clear()
                    inject_frame(wire, 142, {"chatId": 101, "messageIds": [7]})
                    # The sink sets completed for the first three only; use a
                    # protocol round-trip as a receive-loop barrier here.
                    wire.reply(Opcode.CHATS_LIST, {"chats": []})
                    await asyncio.wait_for(client.catalog_page(NOW_MS), 2)
                    batch = seen[3:]
                    assert len(batch) == 1
                keys = [row[3].rsplit(":", 1) for row in batch]
                prefix = keys[0][0]
                UUID(prefix)
                assert all(key[0] == prefix for key in keys)
                assert [int(key[1]) for key in keys] == list(range(1, len(batch) + 1))
                assert all(lower <= row[2] <= datetime.now(timezone.utc) for row in batch)
                prefixes.append(prefix)
            finally:
                await client.close()
        assert prefixes[0] != prefixes[1]

    asyncio.run(scenario())
    assert_read_only(wire)


def test_receive_hook_only_admits_requested_supported_notifications(tmp_path, wire):
    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        seen = []

        async def sink(*args):
            seen.append(args)

        client = AccountClient(path)
        try:
            await client.connect()
            # Pre-identity notifications must not enter the durable sink.
            inject_frame(wire, 128, message(text=SECRET_TEXT))
            wire.reply(Opcode.CHATS_LIST, {"chats": []})
            await asyncio.wait_for(client.catalog_page(NOW_MS), 2)
            client.sink = sink
            inject_frame(wire, 128, message(), cmd=Command.RESPONSE)
            inject_frame(wire, 67, message(), cmd=Command.ERROR)
            inject_frame(wire, Opcode.PING, {})
            for opcode, payload in [(128, message()), (67, message()),
                                    (142, {"chatId": 101, "messageIds": [7]}),
                                    (135, chat()), (140, {"chatId": 101})]:
                inject_frame(wire, opcode, payload)
            wire.reply(Opcode.CHATS_LIST, {"chats": []})
            await asyncio.wait_for(client.catalog_page(NOW_MS), 2)
            assert [row[0] for row in seen] == [128, 67, 142, 135, 140]
            assert [int(row[3].rsplit(":", 1)[1]) for row in seen] == [1, 2, 3, 4, 5]
        finally:
            await client.close()

    asyncio.run(scenario())


def test_receive_hook_admission_failure_closes_without_admitting_later_frames(tmp_path, wire, caplog):
    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        attempted = []

        async def sink(opcode, payload, observed_at, key):
            attempted.append(key)
            raise RuntimeError("synthetic commit failure " + SECRET_TEXT)

        client = AccountClient(path)
        try:
            await client.connect()
            client.sink = sink
            inject_frame(wire, 128, message())
            inject_frame(wire, 67, message(text="later"))
            with pytest.raises(ConnectionError):
                await asyncio.wait_for(client.wait_closed(), 2)
            assert not client.connected
            assert len(attempted) == 1
        finally:
            await client.close()

    asyncio.run(scenario())
    assert_no_secrets(caplog.text)


def test_close_waits_for_inflight_admission_instead_of_abandoning_sql(tmp_path, wire):
    async def scenario():
        path = tmp_path / "account.db"
        await save_session(path)
        entered, release = asyncio.Event(), asyncio.Event()
        committed = []

        async def sink(opcode, payload, observed_at, key):
            entered.set()
            await release.wait()
            committed.append(key)

        client = AccountClient(path)
        closing = None
        try:
            await client.connect()
            client.sink = sink
            inject_frame(wire, 128, message())
            await asyncio.wait_for(entered.wait(), 2)
            closing = asyncio.create_task(client.close())
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not closing.done()
            assert not committed
            assert not wire.sockets[-1].closed
            release.set()
            await asyncio.wait_for(closing, 2)
            assert len(committed) == 1
            assert wire.sockets[-1].closed
        finally:
            release.set()
            if closing is not None:
                await closing
            else:
                await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("opcode", [128, 67])
def test_notification_message_identity_uses_direct_native_payload_only(opcode):
    raw = message("9223372036854775807", text=SECRET_TEXT, sender=TOKEN,
                  attaches=[{"type": "PHOTO", "baseUrl": QR_LINK}], seq=123, prevMessageId=456)
    assert normalize_event(opcode, raw) == {
        "kind": "message", "raw_chat_id": 101, "message_ids": [2**63 - 1]}
    assert normalize_event(opcode, {**raw, "status": "REMOVED"}) == {
        "kind": "removed", "raw_chat_id": 101, "message_ids": [2**63 - 1]}
    assert_no_secrets(repr(normalize_event(opcode, raw)))


def test_notification_delete_metadata_and_unknown_range_keep_no_content():
    assert normalize_event(142, {"chatId": "101", "messageIds": ["7", 2**63 - 1],
                                 "text": SECRET_TEXT}) == {
        "kind": "removed", "raw_chat_id": 101, "message_ids": [7, 2**63 - 1]}
    assert normalize_event(135, {"chat": chat(lastMessage=message(text=SECRET_TEXT),
                                             pinnedMessage=message(text=SECRET_TEXT))}) == {
        "kind": "metadata", "raw_chat_id": 101, "status": "ACTIVE"}
    assert normalize_event(140, {"chatId": 101, "from": 1, "to": 99,
                                 "messages": [message(text=SECRET_TEXT)]}) == {
        "kind": "reconcile_deleted", "raw_chat_id": 101}


@pytest.mark.parametrize("opcode,payload", [
    (128, message(id=True)), (67, message(id=1.5)),
    (128, {"chatId": 101, "message": message(text=SECRET_TEXT)}),
    (142, {"chatId": 101, "messageIds": "7"}),
    (142, {"chatId": 101, "messageIds": [7, False]}),
])
def test_malformed_known_notification_is_safe_invalid_identity(opcode, payload):
    assert normalize_event(opcode, payload) == {"kind": "invalid", "raw_chat_id": 101}


@pytest.mark.parametrize("opcode,payload", [
    (128, None), (128, []), (128, {"id": 7}),
    (128, {"chatId": True, "id": 7}), (142, {"chatId": "opaque", "messageIds": [7]}),
    (135, {"chat": None}), (135, {"chat": chat(raw_id=10**13)}),
])
def test_notification_without_safe_source_identity_raises(opcode, payload):
    with pytest.raises(ProtocolError):
        normalize_event(opcode, payload)


@pytest.mark.parametrize("opcode", [128, 67, 142, 140])
def test_comment_notifications_are_excluded_before_identity_admission(opcode):
    assert normalize_event(opcode, {"postId": 88, "chatId": 101, "id": 7,
                                     "messageIds": [7], "text": SECRET_TEXT}) is None


def test_dialog_metadata_does_not_create_catalog_or_retain_private_content():
    assert normalize_event(135, {"chat": chat(kind="DIALOG", lastMessage=message(text=SECRET_TEXT))}) is None


def test_strict_publication_missing_redis_is_an_error_not_acknowledgement(monkeypatch):
    from catix.ingest import publish

    monkeypatch.setattr(publish.settings, "redis_url", None)

    async def scenario():
        with pytest.raises(RuntimeError, match="publication_error"):
            await publish.publish([(101, 7)], strict=True)
        await publish.publish([(101, 7)])

    asyncio.run(scenario())


def test_strict_publication_propagates_redis_failure_and_best_effort_stays_safe(monkeypatch, caplog):
    from catix.ingest import publish

    class BrokenPipeline:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def xadd(self, *args, **kwargs):
            return self

        async def execute(self):
            raise ConnectionError("synthetic redis failure " + TOKEN)

    class BrokenRedis:
        def pipeline(self, **kwargs):
            return BrokenPipeline()

    monkeypatch.setattr(publish.settings, "redis_url", "redis://synthetic.invalid")
    monkeypatch.setattr(publish, "_client", BrokenRedis())

    async def scenario():
        with pytest.raises(ConnectionError):
            await publish.publish([(101, 7)], strict=True)
        await publish.publish([(101, 7)])

    asyncio.run(scenario())
    assert_no_secrets(caplog.text)
