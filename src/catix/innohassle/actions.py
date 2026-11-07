"""An OpenAPI catalogue and executor, bounded by a code-owned operation policy.

Documentation supplies parameters, never authority: a new Swagger endpoint, server URL,
security scheme or redirect cannot grant access. Only approved read-only operations run.
Tokens bypass the model; public schemas may be cached, authenticated responses never are.
"""

import json
import re
from dataclasses import dataclass
from http.cookiejar import CookieJar, DefaultCookiePolicy
from typing import Any

import httpx
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from catix.common import cache
from catix.settings import settings

_client = httpx.Client(
    base_url=str(settings.innohassle_api), timeout=httpx.Timeout(20, connect=5), follow_redirects=False,
    cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])),
)
SCHEMA_TTL = 3600
MAX_BYTES = 1_000_000
MAX_ITEMS = 40
MAX_RESULT_CHARS = 20_000


class ActionError(Exception):
    """A safe, user-visible failure: never carries HTTP response bodies or credentials."""


@dataclass(frozen=True)
class Action:
    action_id: str
    service: str
    path: str
    title: str
    keywords: str
    fields: tuple[str, ...]
    note: str
    method: str = "GET"
    query_parameters: tuple[str, ...] = ()
    version: str = "v0"
    requires_token: bool = True

    @property
    def prefix(self) -> str:
        return f"/{self.service}/{self.version}"

    @property
    def namespace(self) -> str:
        return "music" if self.service == "music-room" else self.service.replace("-", "_")


# This is the permission boundary, not a generated list of all endpoints in Swagger.
# Adding an entry requires review of its effects, authentication and response fields.
ACTIONS = {
    "printers.print_get_printers_status": Action(
        "printers.print_get_printers_status", "printers", "/print/get_printers_status",
        "Printer availability, paper and toner / Состояние принтеров, бумага и тонер",
        "printer printers printing paper toner cartridge online offline status available availability "
        "принтер принтеры принтерах печать распечатать бумага бумаги тонер картридж состояние работает доступность",
        ("printer.display_name", "printer.cups_name", "offline", "paper_percentage", "toner_percentage"),
        "offline=false only means reachable, not ready to print. Null percentages mean unknown, not zero. "
        "Read-only: printing, print jobs and scanning are not available.",
    ),
    "maps.scenes_search_areas": Action(
        "maps.scenes_search_areas", "maps", "/scenes/areas/search",
        "Find a room, place or printer on the campus map / Найти аудиторию, место или принтер на карте",
        "map room rooms location printer printers аудитория аудитории кабинет карта принтер принтеры расположение",
        ("scene_id", "area.title", "area.ru_title", "area.description"),
        "Location only, not live printer state or room availability. English keywords can match English map names.",
        query_parameters=("query",), requires_token=False,
    ),
    "maps.scenes_scenes": Action(
        "maps.scenes_scenes", "maps", "/scenes/", "Campus map scenes / Карты кампуса",
        "maps scenes floors buildings карта карты этаж этажи здание",
        ("scene_id", "title", "ru_title"), "Map scenes only; use area search to locate a specific room.", requires_token=False,
    ),
    "clubs.get_clubs_list_clubs__get": Action(
        "clubs.get_clubs_list_clubs__get", "clubs", "/clubs/", "University clubs / Университетские клубы",
        "clubs hobby community клуб клубы кружки объединения",
        ("title", "short_description", "is_active"), "Report truncation; is_active=false means the club is not active.", requires_token=False,
    ),
    "music-room.bookings_daily_bookings": Action(
        "music-room.bookings_daily_bookings", "music-room", "/bookings/daily_bookings",
        "Music room bookings for a day / Занятость музыкальной комнаты за день",
        "music musical piano bookings schedule музыка музыкальная музыкальной музкомната музкомнаты брони занятость",
        ("time_start", "time_end"), "Occupied slots only; does not book the music room. Times are local to Innopolis. "
        "The response does not give opening hours. Do not infer free slots: report the occupied intervals only.",
        query_parameters=("date",), requires_token=False,
    ),
    "events.events_list_events": Action(
        "events.events_list_events", "events", "/events/", "Published university events / Мероприятия университета",
        "events event activities lecture workshop мероприятия мероприятие события лекция воркшоп",
        ("id", "data.name", "data.starts_at", "data.duration_hours", "data.location.display_name"),
        "Published events; optional from/to date-time range. Defaults to the current month. No enrolment or participant data.",
        query_parameters=("from", "to", "club"), version="v1", requires_token=False,
    ),
}


def _action(action_id: str) -> Action:
    action = ACTIONS.get(action_id)
    if action is None or action.method != "GET":
        raise ActionError("This API action is not allowed. Search the available actions; no request was sent.")
    return action


def _json(path: str, token: str | None = None, parameters: dict | None = None) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with _client.stream("GET", path, headers=headers, params=parameters, follow_redirects=False) as response:
            if response.status_code == 401:
                raise ActionError("InNoHassle did not accept the sign-in: sign in on the site again.")
            if response.status_code == 403:
                raise ActionError("This account does not have permission for that API action.")
            if response.status_code != 200:
                raise ActionError("InNoHassle API is unavailable or refused the request. Try again later.")
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                if len(raw) > MAX_BYTES:
                    raise ActionError("InNoHassle returned an oversized response; it was not used.")
            return json.loads(raw)
    except (httpx.HTTPError, ValueError):
        raise ActionError("InNoHassle API is unavailable or returned unreadable JSON. Try again later.") from None


def _resolve(value: Any, document: dict, trail: tuple[str, ...] = ()) -> Any:
    """Resolve only local references. Never let a schema validator fetch an arbitrary URL."""
    if isinstance(value, list):
        return [_resolve(item, document, trail) for item in value]
    if not isinstance(value, dict):
        return value
    if "$dynamicRef" in value or "$recursiveRef" in value or "$id" in value:
        raise ActionError("The API schema uses unsupported references; this action cannot run.")
    if "$ref" in value:
        ref = value["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in trail or len(trail) >= 12:
            raise ActionError("The API schema uses unsupported references; this action cannot run.")
        target = document
        try:
            for part in ref[2:].split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError):
            raise ActionError("The API schema has a missing reference; this action cannot run.") from None
        resolved = _resolve(target, document, (*trail, ref))
        siblings = _resolve({key: item for key, item in value.items() if key != "$ref"}, document, trail)
        return {"allOf": [resolved, siblings]} if siblings else resolved
    return {key: _resolve(item, document, trail) for key, item in value.items()}


def _operation(action: Action) -> tuple[dict, dict]:
    key = f"api-actions:openapi:{str(settings.innohassle_api).rstrip('/')}:{action.service}:{action.version}"
    document = cache.cached(key, SCHEMA_TTL, lambda: _json(f"{action.prefix}/openapi.json"))
    try:
        if not document["openapi"].startswith("3.1."):
            raise ActionError("Unsupported OpenAPI version; this action cannot run.")
        path = document["paths"][action.path]
        operation = path[action.method.lower()]
        parameters = _resolve([*path.get("parameters", []), *operation.get("parameters", [])], document)
        # No path substitution, header/cookie parameters, upload or request-body capability is exposed in this read-only pilot.
        if operation.get("requestBody") or any(p["in"] != "query" for p in parameters):
            raise ActionError("The API action now needs unsupported parameters; it cannot run.")
        if any(p["name"] not in action.query_parameters for p in parameters):
            raise ActionError("The API documentation declares unapproved parameters; this action cannot run.")
        if len({p["name"] for p in parameters}) != len(parameters):
            raise ActionError("The API schema has ambiguous parameters; this action cannot run.")
        inputs = {"type": "object", "properties": {p["name"]: p["schema"] for p in parameters},
                  "required": [p["name"] for p in parameters if p.get("required")], "additionalProperties": False}
        output = _resolve(operation["responses"]["200"]["content"]["application/json"]["schema"], document)
        Draft202012Validator.check_schema(inputs)
        Draft202012Validator.check_schema(output)
        _visible_schema(output, action.fields)
        return inputs, output
    except (KeyError, TypeError, AttributeError, SchemaError):
        raise ActionError("The API documentation is unavailable or has an unsupported schema; this action cannot run.") from None


def find(query: str) -> dict:
    words = re.findall(r"[\w]+", query.casefold())
    ranked = []
    for action in ACTIONS.values():
        text = f"{action.title} {action.keywords}".casefold()
        score = sum(word in text for word in words if len(word) > 2)
        if score:
            # A discovery hit must have usable live documentation, not just a hard-coded capability claim.
            _operation(action)
            ranked.append((score, action))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].action_id))
    return {"actions": [{"action_id": a.action_id, "description": a.title, "requires_sign_in": a.requires_token,
                         "read_only": True} for _, a in ranked[:5]],
            "scope": "Only explicitly allowed read-only API operations are searchable."}


def _visible_schema(schema: Any, fields: tuple[str, ...], *, kind: str = "array") -> dict:
    """Validate the pilot's list/record/scalar projection before any authenticated request.

    JSON Schema validity alone does not make a shape projectable. Object compositions
    (including resolved ref siblings) need a reviewed projection; do not invent fields.
    Scalar anyOf is supported for the current printer API's nullable percentages.
    """
    error = "The API has an unsupported response schema; this action cannot run."
    unsupported = {"allOf", "oneOf", "not", "if", "then", "else", "dependentSchemas", "prefixItems", "contains"}
    if not isinstance(schema, dict) or unsupported.intersection(schema):
        raise ActionError(error)
    if kind == "scalar":
        types = schema.get("type", [])
        types = [types] if isinstance(types, str) else types
        if (not types and "anyOf" not in schema) or any(
            t not in {"string", "number", "integer", "boolean", "null"} for t in types
        ):
            raise ActionError(error)
        visible = {k: v for k, v in schema.items() if k in {"type", "enum"}}
        if "anyOf" in schema:
            visible["anyOf"] = [_visible_schema(branch, (), kind="scalar") for branch in schema["anyOf"]]
        return visible
    if schema.get("type") != kind or "anyOf" in schema:
        raise ActionError(error)
    if kind == "array":
        return {"type": "array", "items": _visible_schema(schema.get("items"), fields, kind="object")}
    properties = {}
    for field in fields:
        first, _, rest = field.partition(".")
        source = schema.get("properties", {}).get(first)
        nested = tuple(f.partition(".")[2] for f in fields if f.startswith(first + ".")) if rest else ()
        properties[first] = _visible_schema(source, nested, kind="object" if rest else "scalar")
    return {"type": "object", "properties": properties}


def describe(action_id: str) -> dict:
    action = _action(action_id)
    inputs, output = _operation(action)
    return {"action_id": action_id, "description": action.title, "method": action.method,
            "path": action.prefix + action.path, "parameters": inputs,
            "returns": _visible_schema(output, action.fields), "requires_sign_in": action.requires_token,
            "read_only": True, "requires_approval": False, "note": action.note}


def _project(item: dict, fields: tuple[str, ...]) -> dict:
    out = {}
    for field in fields:
        parts = field.split(".")
        source, target = item, out
        for part in parts[:-1]:
            source = source[part]
            target = target.setdefault(part, {})
        value = source[parts[-1]]
        if isinstance(value, (dict, list)):
            raise ValueError("an allowed leaf cannot expose arbitrary nested fields")
        target[parts[-1]] = value
    return out


def execute(action_id: str, parameters: dict, token: str | None) -> dict:
    action = _action(action_id)
    if action.requires_token and not token:
        raise ActionError("This API action requires sign in on the site innohassle.ru.")
    inputs, output = _operation(action)
    try:
        Draft202012Validator(inputs, format_checker=FormatChecker()).validate(parameters)
    except ValidationError:
        raise ActionError("Invalid API parameters. Use the discovered tool's inputSchema and supply only its required/allowed parameters.") from None
    parameters = {key: value for key, value in parameters.items() if value is not None or key in inputs["required"]}
    # Public services must not receive a caller's credentials even when the caller has signed in.
    data = _json(action.prefix + action.path, token if action.requires_token else None, parameters)
    try:
        Draft202012Validator(output).validate(data)
        # The read-only pilot admits lists of records. Other output shapes need a reviewed policy, not model guesses.
        if not isinstance(data, list):
            raise ValueError("not a list")
        visible = [_project(item, action.fields) for item in data[:MAX_ITEMS]]
        if len(json.dumps(visible, ensure_ascii=False)) > MAX_RESULT_CHARS:
            raise ValueError("result too large")
    except (ValidationError, KeyError, TypeError, ValueError):
        raise ActionError("InNoHassle returned an unexpected response; no reliable result is available.") from None
    return {"action_id": action_id, "data": visible, "total": len(data), "truncated": len(data) > MAX_ITEMS,
            "note": action.note}
