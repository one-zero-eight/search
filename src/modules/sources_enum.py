from enum import StrEnum

from src.storages.mongo import CampusLifeEntry, EduWikiEntry, HotelEntry, MoodleEntry


# Currently supported list of sources we use information from.
# To add new source add it here, in ml service, in parser.
class InfoSources(StrEnum):
    moodle = "moodle"
    eduwiki = "eduwiki"
    campuslife = "campuslife"
    hotel = "hotel"


InfoSourcesToMongoEntry = {
    InfoSources.moodle: MoodleEntry,
    InfoSources.eduwiki: EduWikiEntry,
    InfoSources.campuslife: CampusLifeEntry,
    InfoSources.hotel: HotelEntry,
}

InfoSourcesToMongoEntryName = {
    InfoSources.moodle: "MoodleEntry",
    InfoSources.eduwiki: "EduWikiEntry",
    InfoSources.campuslife: "CampusLifeEntry",
    InfoSources.hotel: "HotelEntry",
}
