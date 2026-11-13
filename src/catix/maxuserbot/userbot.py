"""Terminal-only MAX account login and read-only catalog commands."""

import argparse
import asyncio
import getpass
import json
import sys
import time
from pathlib import Path


class _CommandError(Exception):
    """An error whose fixed message is safe to show in the terminal."""


def _require_terminal() -> None:
    if not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr)):
        raise _CommandError("login_requires_tty: run login in an interactive terminal")


class _TerminalQrProvider:
    async def show_qr(self, qr_url: str) -> None:
        _require_terminal()
        import qrcode

        qr = qrcode.QRCode()
        qr.add_data(qr_url)
        qr.make(fit=True)
        print("Scan this QR code in the MAX application:", flush=True)
        qr.print_ascii(out=sys.stdout, tty=False)
        sys.stdout.flush()


class _TerminalPasswordProvider:
    async def get_password(self, hint: str | None = None) -> str:
        # Server-provided hints can contain personal information: never print them.
        _require_terminal()
        return await asyncio.to_thread(getpass.getpass, "MAX 2FA password: ")


def _session_files(session: Path) -> tuple[Path, ...]:
    return (session, *(Path(f"{session}{suffix}") for suffix in ("-journal", "-wal", "-shm")))


def _secure_session_files(session: Path) -> None:
    for path in _session_files(session):
        if path.is_symlink():
            raise _CommandError("session_path_unsafe: session files must not be symlinks")
        try:
            path.chmod(0o600)
        except FileNotFoundError:
            pass


def _replace_session(session: Path) -> None:
    _require_terminal()
    print("Replace the local MAX session? This does not log out other devices.")
    if input("Type REPLACE to confirm: ") != "REPLACE":
        raise _CommandError("login_cancelled: local session was not replaced")
    for path in _session_files(session):
        path.unlink(missing_ok=True)


def _print_chat(chat: dict) -> None:
    # Escape untrusted metadata, including terminal control characters.
    print(json.dumps({"raw_chat_id": chat["raw_chat_id"], "kind": chat["kind"], "title": chat.get("title", "")}, ensure_ascii=True))


async def _catalog(client) -> None:
    marker = time.time_ns() // 1_000_000
    seen_markers = {marker}
    seen_chats: set[int] = set()

    def display(chats: list[dict]) -> None:
        for chat in chats:
            if chat.get("kind") not in {"chat", "channel"}:
                continue
            if chat["raw_chat_id"] not in seen_chats:
                seen_chats.add(chat["raw_chat_id"])
                _print_chat(chat)

    while True:
        chats, next_marker = await client.catalog_page(marker)
        display(chats)
        # Empty sanitized pages may contain only excluded DIALOGs upstream.
        # The adapter rejects an absent marker on nonempty raw pages.
        if next_marker is None or next_marker == 0:
            break
        if next_marker in seen_markers:
            raise _CommandError("catalog_cursor_stalled: catalog may be incomplete")
        seen_markers.add(next_marker)
        marker = next_marker
    display(client.login_chats)


async def _account_command(args: argparse.Namespace, session: Path) -> None:
    from .client import AccountClient

    if args.command == "login":
        _require_terminal()
        if args.replace:
            _replace_session(session)
        client = AccountClient(
            session,
            login=True,
            qr_provider=_TerminalQrProvider(),
            password_provider=_TerminalPasswordProvider(),
        )
    else:
        client = AccountClient(session)
    try:
        await client.connect()
        if args.command == "login":
            # Accessing the validated profile is part of successful login.
            account_id = client.account_id
        else:
            await _catalog(client)
    finally:
        try:
            await client.close()
        finally:
            _secure_session_files(session)
    if args.command == "login":
        print(f"MAX login successful (account {account_id}).")


async def _execute(args: argparse.Namespace) -> None:
    # Import settings only after parsing: --help needs no environment, DB or network.
    from catix.settings import settings

    from .client import SessionLock

    session = Path(settings.max_session)
    if args.command == "login":
        _require_terminal()
    with SessionLock(session):
        _secure_session_files(session)
        if args.command == "listen":
            from .client import AccountClient

            preflight = AccountClient(session)
            try:
                await preflight.require_session()
            finally:
                await preflight.close()
            from .worker import run

            await run()
        else:
            await _account_command(args, session)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catix-maxuserbot", description=__doc__)
    commands = parser.add_subparsers(dest="command")
    login = commands.add_parser("login", help="log in using a QR code in an interactive terminal")
    login.add_argument("--replace", action="store_true", help="confirm and remove the local session before login")
    commands.add_parser("chats", help="list account groups and channels without logging in")
    commands.add_parser("listen", help="listen using an existing account session (default)")
    parser.set_defaults(command="listen")
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        asyncio.run(_execute(args))
    except _CommandError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
    except (KeyboardInterrupt, EOFError):
        print("cancelled", file=sys.stderr)
        raise SystemExit(130) from None
    except Exception as exc:
        # Upstream exception text and tracebacks can contain tokens.
        from .client import LoginRequired, ProtocolError, SessionBusy

        if isinstance(exc, LoginRequired):
            message = "login_required: run catix-maxuserbot login in an interactive terminal"
        elif isinstance(exc, ProtocolError):
            if getattr(exc, "code", None) == "catalog_pagination_unknown":
                message = "catalog_pagination_unknown: catalog may be incomplete"
            else:
                message = "protocol_error: MAX returned an unsupported response"
                if exc.detail:
                    message += f" ({exc.detail})"
        elif isinstance(exc, (SessionBusy, BlockingIOError)):
            message = "session_locked: another MAX command is using this session"
        elif getattr(exc, "code", None) == "worker_locked":
            message = "worker_locked: another MAX listener holds the account database lock"
        elif getattr(exc, "code", None) == "worker_lock_lost":
            message = "worker_lock_lost: listener stopped after losing the account database lock"
        elif getattr(exc, "code", None) == "account_mismatch":
            message = "account_mismatch: the MAX session belongs to a different configured account"
        else:
            message = f"{args.command}_failed: MAX command did not complete"
        print(message, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
