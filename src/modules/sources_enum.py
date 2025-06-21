from enum import StrEnum


# Currently supported list of sources we use information from.
# To add new source add it here, in ml service, in parser.
class InfoSources(StrEnum):
    moodle = "moodle"
    eduwiki = "eduwiki"
    campuslife = "campuslife"
    hotel = "hotel"
