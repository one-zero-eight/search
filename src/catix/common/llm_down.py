"""The language model cannot be reached: the agent says so instead of a vague failure."""

import httpx

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

UNAVAILABLE = "Ассистент сейчас не работает: нет связи с языковой моделью. Попробуйте, пожалуйста, чуть позже."

_NETWORK = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError, ConnectionError, TimeoutError)


def unreachable(error: BaseException) -> bool:
    """True when the error, or what caused it, is a lost connection to the model (or its 502/503/504)."""
    seen: set[int] = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, _NETWORK):
            return True
        if openai is not None:
            if isinstance(error, openai.APIConnectionError):  # includes APITimeoutError
                return True
            if isinstance(error, openai.APIStatusError) and error.status_code in (502, 503, 504):
                return True
        error = error.__cause__ or error.__context__
    return False
