from src.modules.parsers.campus_life.clubs import parse as parse_clubs
from src.modules.parsers.campus_life.handbook import parse as parse_handbook


def parse():
    result = parse_clubs()
    result += parse_handbook()
    return result
