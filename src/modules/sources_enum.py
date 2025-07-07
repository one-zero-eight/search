from enum import StrEnum
from typing import Final

from src.storages.mongo import (
    CampusLifeEntry,
    EduWikiEntry,
    HotelEntry,
    InNoHassleEntry,
    MapsEntry,
    MoodleEntry,
    MyUniEntry,
    ResidentsEntry,
)
from src.storages.mongo.__base__ import CustomDocument


# Currently supported list of sources we use information from.
# To add new source add it here, in ml service, in parser.
class InfoSources(StrEnum):
    moodle = "moodle"
    eduwiki = "eduwiki"
    campuslife = "campuslife"
    hotel = "hotel"
    maps = "maps"
    residents = "residents"
    myuni = "myuni"
    innohassle = "innohassle"


ALL_SOURCES = list(InfoSources)

InfoSourcesToMongoEntry: Final[dict[InfoSources, type[CustomDocument]]] = {
    InfoSources.moodle: MoodleEntry,
    InfoSources.eduwiki: EduWikiEntry,
    InfoSources.campuslife: CampusLifeEntry,
    InfoSources.hotel: HotelEntry,
    InfoSources.maps: MapsEntry,
    InfoSources.residents: ResidentsEntry,
    InfoSources.myuni: MyUniEntry,
    InfoSources.innohassle: InNoHassleEntry,
}

InfoSourcesToMongoEntryName: Final[dict[InfoSources, str]] = {
    InfoSources.moodle: "MoodleEntry",
    InfoSources.eduwiki: "EduWikiEntry",
    InfoSources.campuslife: "CampusLifeEntry",
    InfoSources.hotel: "HotelEntry",
    InfoSources.maps: "MapsEntry",
    InfoSources.residents: "ResidentsEntry",
    InfoSources.myuni: "MyUniEntry",
    InfoSources.innohassle: "InNoHassleEntry",
}
