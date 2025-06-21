from fastapi import APIRouter, HTTPException

from src.api.logging_ import logger
from src.modules.parsers.campus_life.parser import parse as parse_campus_life
from src.modules.parsers.eduwiki.parser import parse as parse_eduwiki
from src.modules.parsers.hotel.parser import parse as parse_hotel
from src.modules.sources_enum import InfoSources
from src.storages.mongo.campus_life import CampusLifeEntry
from src.storages.mongo.edu_wiki import EduWikiEntry
from src.storages.mongo.hotel import HotelEntry

router = APIRouter()


@router.post("/{section}/parse")
async def upload_markdown_file(section: InfoSources):
    if section == InfoSources.hotel:
        parse_func, model_class = parse_hotel, HotelEntry
    elif section == InfoSources.eduwiki:
        parse_func, model_class = parse_eduwiki, EduWikiEntry
    elif section == InfoSources.campuslife:
        parse_func, model_class = parse_campus_life, CampusLifeEntry
    else:
        raise HTTPException(status_code=400, detail=f"Not supported section: {section}")

    try:
        await model_class.get_motor_collection().delete_many({})

        all_entries = parse_func()
        logger.info(f"{section} section entries parsed")

        for entry in all_entries:
            doc = model_class.model_validate(entry, from_attributes=True)
            await doc.save()

        return {"message": f"{len(all_entries)} documents saved successfully.", "entries": all_entries}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during parsing or saving: {e}")
