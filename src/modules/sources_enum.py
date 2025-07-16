from enum import StrEnum
from typing import Final


# Currently supported list of sources we use information from.
# To add new source add it here, in ml service, in parser.
class InfoSources(StrEnum):
    moodle = "moodle"
    eduwiki = "eduwiki"
    campuslife = "campuslife"
    hotel = "hotel"
    maps = "maps"
    residents = "residents"
    resources = "resources"


ALL_SOURCES = list(InfoSources)


from src.storages.mongo import (  # noqa: E402
    CampusLifeEntry,
    EduWikiEntry,
    HotelEntry,
    MapsEntry,
    MoodleEntry,
    ResidentsEntry,
    ResourcesEntry,
)
from src.storages.mongo.__base__ import CustomDocument  # noqa: E402

InfoSourcesToMongoEntry: Final[dict[InfoSources, type[CustomDocument]]] = {
    InfoSources.moodle: MoodleEntry,
    InfoSources.eduwiki: EduWikiEntry,
    InfoSources.campuslife: CampusLifeEntry,
    InfoSources.hotel: HotelEntry,
    InfoSources.maps: MapsEntry,
    InfoSources.residents: ResidentsEntry,
    InfoSources.resources: ResourcesEntry,
}

InfoSourcesToMongoEntryName: Final[dict[InfoSources, str]] = {
    InfoSources.moodle: "MoodleEntry",
    InfoSources.eduwiki: "EduWikiEntry",
    InfoSources.campuslife: "CampusLifeEntry",
    InfoSources.hotel: "HotelEntry",
    InfoSources.maps: "MapsEntry",
    InfoSources.residents: "ResidentsEntry",
    InfoSources.resources: "ResourcesEntry",
}
