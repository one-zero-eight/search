"""All pinned PyMax internals live here. No interactive authentication in daemons."""

import asyncio
from contextlib import AbstractContextManager
from datetime import datetime, timezone
import fcntl
import logging
import os
from pathlib import Path
from uuid import uuid4

from pymax.auth.base import AuthFlow
from pymax.auth.qr import QrAuthFlow
from pymax.client_web import WebClient
from pymax.config import ExtraConfig
from pymax.connection import ConnectionManager
from pymax.connection.readers import WSReader
from pymax.exceptions import ApiError
from pymax.protocol import Command
from pymax.protocol.tcp import TcpProtocol
from pymax.session import SessionStore
from pymax.transport.websocket import WebSocketTransport

from .models import ProtocolError, normalize_chat, normalize_id, normalize_message


class LoginRequired(Exception):
    code = "login_required"

    def __init__(self):
        super().__init__("login_required: run catix-maxuserbot login in a terminal")


class SessionBusy(Exception):
    pass


def classify_error(exc: Exception) -> str:
    if isinstance(exc, LoginRequired):
        return "login_required"
    if isinstance(exc, ApiError) and any(value in (exc.error, exc.message)
                                       for value in ("FAIL_LOGIN_TOKEN", "FAIL_LOGOUT_ALL")):
        return "login_required"
    if isinstance(exc, ProtocolError):
        return exc.code
    return "processing_error"


class SessionLock(AbstractContextManager):
    """Lock before opening SQLite; umask covers SQLite sidecars too."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.fd = None
        self.umask = None

    def __enter__(self):
        self.umask = os.umask(0o077)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.path.parent.chmod(0o700)
            lock = self.path.with_name(self.path.name + ".lock")
            self.fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            os.fchmod(self.fd, 0o600)
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SessionBusy("MAX session is already in use") from None
            for suffix in ("", "-journal", "-wal", "-shm"):
                file = Path(str(self.path) + suffix)
                if file.is_symlink():
                    raise ValueError("MAX session must not be a symlink")
                if file.exists():
                    file.chmod(0o600)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.umask is not None:
            os.umask(self.umask)
            self.umask = None


class _Quiet(logging.Filter):
    def filter(self, record):
        return False


def _silence_transport():
    # Ancestor filters do not filter propagated child records: stop propagation.
    # aiosqlite debug records include bound SQLite credentials.
    for name in ("pymax", "websockets", "aiosqlite"):
        logger = logging.getLogger(name)
        logger.handlers[:] = [logging.NullHandler()]
        logger.propagate = False
        logger.addFilter(_Quiet())
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger) and name.startswith(("pymax.", "websockets.", "aiosqlite.")):
            logger.handlers.clear()
            logger.propagate = True


class _NoLogin(AuthFlow):
    async def authenticate(self, app):
        raise LoginRequired()


class _IngressConnection(ConnectionManager):
    def __init__(self, *, owner, **kwargs):
        super().__init__(**kwargs)
        self.owner = owner
        self.connection_id = uuid4().hex
        self.ordinal = 0
        self.admission_order = asyncio.Lock()

    async def _handle_inbound(self, frame):
        observed_at = datetime.now(timezone.utc)
        async with self.admission_order:
            if self.owner.sink is not None and frame.cmd == Command.REQUEST and frame.opcode in {128, 67, 142, 135, 140}:
                self.ordinal += 1
                task = asyncio.create_task(self.owner.sink(frame.opcode, frame.payload, observed_at,
                                                           f"{self.connection_id}:{self.ordinal}"))
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    await task
                    raise
            await super()._handle_inbound(frame)


class _PassiveWebClient(WebClient):
    def __init__(self, *, owner, **kwargs):
        self.owner = owner
        super().__init__(**kwargs)

    async def _prepare_config(self):
        config = await super()._prepare_config()
        config.interactive = False
        return config

    def _build_connection(self):
        transport = WebSocketTransport(url=self.extra_config.url, proxy=self.extra_config.proxy)
        return _IngressConnection(owner=self.owner, transport=transport,
                                  reader=WSReader(transport=transport), protocol=TcpProtocol())


class AccountClient:
    def __init__(self, session: Path, *, login=False, qr_provider=None, password_provider=None):
        self.session = Path(session)
        self.login = login
        self.sink = None  # Enabled by worker only after account identity check.
        self.store = SessionStore(str(self.session.parent), self.session.name)
        flow = QrAuthFlow(qr_provider, password_provider) if login else _NoLogin()
        _silence_transport()
        self._client = _PassiveWebClient(owner=self, session_name=self.session.name,
            work_dir=str(self.session.parent), auth_flow=flow,
            extra_config=ExtraConfig(store=self.store, relogin=False, telemetry=False,
                                     reconnect=False, log_level="CRITICAL", request_timeout=30,
                                     password_max_attempts=3))
        _silence_transport()  # WebClient configures its own handlers.

    async def require_session(self):
        if not self.session.is_file() or not await self.store.load_session():
            raise LoginRequired()

    async def connect(self):
        if not self.login:
            await self.require_session()
        try:
            await self._client.connect()
            if not self._client.is_connected or self._client.me is None:
                raise ProtocolError(detail="login: connection or profile unavailable")
        except ApiError as exc:
            if self._client._app._is_invalid_login_token_error(exc):
                raise LoginRequired() from None
            raise

    async def close(self):
        try:
            await self._client.close()
        finally:
            await self.store.close()

    @property
    def account_id(self):
        return normalize_id(self._client.me.contact.id)

    @property
    def connected(self):
        return self._client.is_connected

    @property
    def login_chats(self):
        return [chat for item in (self._client.chats or [])
                if (chat := normalize_chat(item.model_dump(by_alias=True))) is not None]

    async def wait_closed(self):
        await self._client._connection.wait_closed()

    async def ordered_heartbeat(self, callback):
        connection = self._client._connection
        async with connection.admission_order:
            if connection.is_open:
                task = asyncio.create_task(callback())
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    await task
                    raise

    async def _rpc(self, opcode, payload):
        frame = await self._client._app.invoke(opcode=opcode, payload=payload)
        if not isinstance(frame.payload, dict):
            raise ProtocolError(detail="rpc.payload: expected object")
        return frame.payload

    async def catalog_page(self, marker: int):
        payload = await self._rpc(53, {"marker": normalize_id(marker)})
        chats = payload.get("chats")
        if not isinstance(chats, list):
            raise ProtocolError(detail="catalog.chats: expected array")
        result = [chat for raw in chats if (chat := normalize_chat(raw)) is not None]
        if not chats:
            return result, None
        if "marker" not in payload:
            error = ProtocolError("catalog_pagination_unknown")
            error.page = result
            raise error
        try:
            marker = normalize_id(payload["marker"])
        except ProtocolError:
            raise ProtocolError(detail="catalog.marker: expected int64 or ASCII decimal ID") from None
        return result, marker or None

    async def chat(self, raw_id: int):
        raw_id = normalize_id(raw_id)
        payload = await self._rpc(48, {"chatIds": [raw_id]})
        chats = payload.get("chats")
        if not isinstance(chats, list):
            raise ProtocolError()
        if not chats:
            return {}
        if len(chats) != 1:
            raise ProtocolError()
        chat = normalize_chat(chats[0])
        if chat is None or chat["raw_chat_id"] != raw_id:
            raise ProtocolError()
        return chat

    async def history(self, raw_id: int, before_ms: int, *, backward=100):
        raw_id, before_ms = normalize_id(raw_id), normalize_id(before_ms)
        if before_ms < 0:
            raise ProtocolError()
        payload = await self._rpc(49, {"chatId": raw_id, "from": before_ms, "backward": backward,
            "forward": 0, "backwardTime": 0, "forwardTime": 0, "getMessages": True,
            "getChat": False, "itemType": "REGULAR", "interactive": False})
        messages = self._validated_messages(payload, raw_id)
        if any(normalize_id(m.get("time", 0)) > before_ms for m in messages):
            raise ProtocolError()
        return messages

    async def messages(self, raw_id: int, ids: list[int]):
        raw_id = normalize_id(raw_id)
        ids = [normalize_id(value) for value in ids]
        payload = await self._rpc(71, {"chatId": raw_id, "messageIds": ids})
        messages = self._validated_messages(payload, raw_id)
        if any(normalize_id(m["id"]) not in ids for m in messages):
            raise ProtocolError()
        return messages

    @staticmethod
    def _validated_messages(payload, raw_id):
        messages = payload.get("messages")
        if not isinstance(messages, list):
            raise ProtocolError()
        for raw in messages:
            normalize_message(raw, raw_id)
        return messages
