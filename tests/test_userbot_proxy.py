"""TG_PROXY for the userbot (tguserbot/userbot.py): where the network blocks Telegram's data centres, the client goes
through an HTTP or SOCKS proxy or an MTProxy. Only the arguments are checked here; nothing connects."""

import pytest
from telethon import TelegramClient
from telethon.network.connection import ConnectionTcpMTProxyRandomizedIntermediate

from catix.tguserbot.userbot import proxy_args


def test_no_proxy_gives_no_arguments():
    assert proxy_args(None) == {} and proxy_args("") == {}


def test_a_socks5_proxy_with_a_password():
    args = proxy_args("socks5://bot:p%40ss@10.0.0.5:1080")
    assert args["proxy"] == {"proxy_type": "socks5", "addr": "10.0.0.5", "port": 1080, "rdns": True, "username": "bot", "password": "p@ss"}


def test_an_http_proxy_with_a_password():
    args = proxy_args("http://bot:secret@proxy.example:3128")
    assert args["proxy"] == {"proxy_type": "http", "addr": "proxy.example", "port": 3128, "rdns": True, "username": "bot", "password": "secret"}


def test_a_proxy_reached_over_tls_is_refused_with_the_way_out():
    with pytest.raises(ValueError, match="http://"):
        proxy_args("https://bot:secret@proxy.example:443")


def test_an_mtproxy():
    args = proxy_args("mtproxy://dd0123456789abcdef0123456789abcdef@proxy.example:443")
    assert args == {"connection": ConnectionTcpMTProxyRandomizedIntermediate,
                    "proxy": ("proxy.example", 443, "dd0123456789abcdef0123456789abcdef")}


@pytest.mark.parametrize("url", ["socks5://host-without-port", "ftp://h:1", "mtproxy://h:443", "mtproxy://ee00@h:443"])
def test_a_malformed_proxy_is_refused(url):
    with pytest.raises(ValueError):
        proxy_args(url)


@pytest.mark.parametrize("url", ["socks5://u:p@127.0.0.1:1080", "http://u:p@127.0.0.1:3128", "mtproxy://dd0123456789abcdef0123456789abcdef@127.0.0.1:443"])
def test_telethon_takes_the_arguments(url, tmp_path):
    TelegramClient(str(tmp_path / "s"), 1, "0" * 32, **proxy_args(url))
