from typing import cast

from beanie import Document, View

from src.storages.mongo.campus_life import CampusLifeEntry
from src.storages.mongo.chat import ChatSession
from src.storages.mongo.edu_wiki import EduWikiEntry
from src.storages.mongo.clubs import ClubsEntry
from src.storages.mongo.hotel import HotelEntry
from src.storages.mongo.maps import MapsEntry
from src.storages.mongo.moodle import MoodleCourse, MoodleEntry
from src.storages.mongo.residents import ResidentsEntry
from src.storages.mongo.resources import ResourcesEntry
from src.storages.mongo.statistics import ActStatistics, AskStatistics, SearchStatistics
from src.storages.mongo.telegram import Message

document_models = cast(
    list[type[Document] | type[View] | str],
    [
        Message,
        MoodleEntry,
        MoodleCourse,
        CampusLifeEntry,
        SearchStatistics,
        AskStatistics,
        ActStatistics,
        CampusLifeEntry,
        EduWikiEntry,
        ClubsEntry,
        HotelEntry,
        MapsEntry,
        ResourcesEntry,
        ResidentsEntry,
        ChatSession,
    ],
)
