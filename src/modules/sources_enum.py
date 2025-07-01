from enum import StrEnum
from typing import Final

from src.storages.mongo import CampusLifeEntry, EduWikiEntry, HotelEntry, MapsEntry, MoodleEntry
from src.storages.mongo.__base__ import CustomDocument


# Currently supported list of sources we use information from.
# To add new source add it here, in ml service, in parser.
class InfoSources(StrEnum):
    moodle = "moodle"
    eduwiki = "eduwiki"
    campuslife = "campuslife"
    hotel = "hotel"
    maps = "maps"


ALL_SOURCES = list(InfoSources)

InfoSourcesToMongoEntry: Final[dict[InfoSources, type[CustomDocument]]] = {
    InfoSources.moodle: MoodleEntry,
    InfoSources.eduwiki: EduWikiEntry,
    InfoSources.campuslife: CampusLifeEntry,
    InfoSources.hotel: HotelEntry,
    InfoSources.maps: MapsEntry,
}

InfoSourcesToMongoEntryName: Final[dict[InfoSources, str]] = {
    InfoSources.moodle: "MoodleEntry",
    InfoSources.eduwiki: "EduWikiEntry",
    InfoSources.campuslife: "CampusLifeEntry",
    InfoSources.hotel: "HotelEntry",
    InfoSources.maps: "MapsEntry",
}
