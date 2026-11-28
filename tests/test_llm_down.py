import httpx
import openai

from catix.common.llm_down import unreachable


def test_connection_errors_are_unreachable():
    request = httpx.Request("POST", "http://llm/v1/chat/completions")
    assert unreachable(openai.APIConnectionError(request=request))
    assert unreachable(httpx.ConnectError("refused"))
    try:
        try:
            raise ConnectionRefusedError("x")
        except ConnectionRefusedError as e:
            raise RuntimeError("wrapped") from e
    except RuntimeError as wrapped:
        assert unreachable(wrapped)


def test_other_errors_are_not():
    assert not unreachable(ValueError("bad"))
