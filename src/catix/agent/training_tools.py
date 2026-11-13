"""Calendar-checked Sport recommendations on the host, never a signup."""

from datetime import date, datetime

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.errors import GraphBubbleUp
from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix.agent.api_tools import _credentials
from catix.agent.schedule_tools import read_my_schedule
from catix.agent.scheduling import ScheduleCheckError, training_conflicts
from catix.innohassle import mcp_client
from catix.settings import settings


def _unavailable(error: str, code: str) -> tuple[dict, None]:
    return {"error": error, "code": code, "complete": False,
            "note": "Personal training availability was not verified. Explain the failure without recommending slots. "
                    "Do not retry this recommendation in the same turn or fall back to sport_get_sport_trainings, "
                    "sport_get_my_sport, or separate calendar reads to calculate alternatives yourself. "
                    "The user may request a new check later."}, None


class AvailableTrainingsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date = Field(description="The requested local date, YYYY-MM-DD. A single day, not a default week.")
    sport: str | None = Field(None, max_length=60, description="Optional sport explicitly requested by the user, in English.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values


@tool(args_schema=AvailableTrainingsArgs, response_format="content_and_artifact")
def get_my_available_trainings(runtime: ToolRuntime, day: date, sport: str | None = None) -> tuple[dict, dict | None]:
    """Sport trainings ONLY for explicit personal-calendar matching on ONE day, including AI Calendar.
    Без пересечений с моими занятиями / which trainings fit my personal schedule.
    Ordinary training lists or recommendations use sport_get_sport_trainings instead, without calendar filtering.
    "For me" or "what can I sign up for" alone does not request calendar matching. Call this native tool directly.
    Only available contains calendar-compatible, signup-eligible alternatives; excluded has reasons/conflicts;
    unverified is NOT free time. Report complete=false/truncated; this is not a reservation or an automatic signup.
    unknown_duration_events identifies events with no known end; ask when they end, not for another calendar read.
    These uncertainties do not invalidate entries in available or definite conflicts in excluded.
    On error, explain that availability could not be checked; do not retry or use raw Sport/calendar reads as a fallback.
    Omit sport unless the user chose it. Ask for the day if unknown. Signup still requires separate user approval and fresh checks.
    """
    try:
        token, credentials = _credentials("sport", runtime)
    except ValueError as error:
        return _unavailable(str(error), "authentication_required")
    period = {"date_from": day.isoformat(), "date_to": day.isoformat()}
    arguments = {**period, **({"sport": sport} if sport is not None else {})}
    try:
        trainings = mcp_client.request_sync("call_tool", {"name": "sport_get_sport_trainings", "arguments": arguments},
                                           token, **credentials)
    except GraphBubbleUp:
        raise
    except Exception:
        return _unavailable("Sport trainings could not be read; availability is unknown.", "sport_unavailable")
    if isinstance(trainings, dict) and "error" in trainings:
        if trainings.get("code") == "upstream_timeout":
            return _unavailable("Sport did not answer in time; personal training availability is unknown.", "upstream_timeout")
        if trainings.get("code") == "mcp_timeout":
            return _unavailable("MCP did not answer in time; personal training availability is unknown.", "mcp_timeout")
        return _unavailable("Sport trainings could not be read; availability is unknown.", "sport_unavailable")
    if (not isinstance(trainings, dict) or trainings.get("range") != [day.isoformat(), day.isoformat()]
            or not isinstance(trainings.get("trainings"), list)):
        return _unavailable("Sport returned an unreadable training list for the requested day; availability is unknown.",
                            "invalid_training_response")
    agenda = read_my_schedule(runtime, day, day)
    available, excluded, unverified = [], [], []
    for candidate in trainings["trainings"]:
        if not isinstance(candidate, dict) or type(candidate.get("training_id")) is not int or candidate["training_id"] <= 0:
            unverified.append({"reason": "invalid_training"})
            continue
        try:
            item, conflicts = training_conflicts(candidate["training_id"], trainings, agenda)
            if conflicts:
                excluded.append({**item, "reason": "schedule_conflict", "conflicts": conflicts})
            else:
                available.append(item)
        except ScheduleCheckError as error:
            collection = excluded if error.result["code"] == "training_unavailable" else unverified
            collection.append({**candidate, "reason": error.result["code"],
                               **{key: error.result[key] for key in ("uncertainty", "unknown_duration_events") if key in error.result}})
    truncated = bool(trainings.get("more") or trainings.get("truncated") or agenda.get("truncated"))
    not_read = list(agenda.get("not_read", []))
    if trainings.get("more") or trainings.get("truncated"):
        not_read.append("Sport training list is truncated; choose a sport to narrow the read.")
    if any(item.get("uncertainty") != "unknown_event_end" for item in unverified):
        not_read.append("Some trainings could not be checked; do not recommend unverified entries.")
    result = {"range": [day.isoformat(), day.isoformat()], "timezone": str(settings.tz),
              "available": available, "excluded": excluded, "unverified": unverified,
              "total": len(available) + len(excluded) + len(unverified), "truncated": truncated,
              "complete": agenda.get("complete") is True and not truncated and not unverified,
              "not_read": not_read, "source_errors": agenda.get("source_errors", {}),
              "checked_at": datetime.now(settings.tz).isoformat()}
    if unverified:
        result["note"] = ("Some trainings could not be checked. If available is empty, lead with uncertainty: "
                          "'Не удалось определить, какие тренировки подходят по вашему расписанию: проверка неполная.' "
                          "Explain the missing data below, not 'подходящих тренировок нет'. "
                          "can_check_in is only Sport eligibility, not personal availability. "
                          "Do not offer signup for unverified slots or repeat reads in this turn. "
                          "If available is nonempty, recommend only those verified entries.")
    return result, {"trainings": trainings, "agenda": agenda, "training_arguments": arguments}
