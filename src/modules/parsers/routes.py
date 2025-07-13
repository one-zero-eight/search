import json

from fastapi import APIRouter, HTTPException

from src.api.logging_ import logger
from src.modules.ml.ml_client import get_ml_service_client
from src.modules.parsers.campus_life.parser import parse as parse_campus_life
from src.modules.parsers.eduwiki.parser import parse as parse_eduwiki
from src.modules.parsers.hotel.parser import parse as parse_hotel
from src.modules.parsers.maps.parser import parse as parse_maps
from src.modules.parsers.residents.parser import parse as parse_residents
from src.modules.sources_enum import InfoSources
from src.modules.static_resources.load_data import load_resources
from src.storages.mongo.__base__ import CustomDocument
from src.storages.mongo.campus_life import CampusLifeEntry
from src.storages.mongo.edu_wiki import EduWikiEntry
from src.storages.mongo.hotel import HotelEntry
from src.storages.mongo.maps import MapsEntry
from src.storages.mongo.residents import ResidentsEntry
from src.storages.mongo.resources import ResourcesEntry

router = APIRouter()


def save_dump(entries):
    filepath = "tests/test_data/data.json"
    mode = "a"

    print("Writing results to file...")

    with open(filepath, mode, encoding="utf-8") as file:
        for entry in entries:
            item = {"model_type": entry.__class__.__name__, "data": entry.dict()}
            obj = json.dumps(item, ensure_ascii=False)
            file.write(obj + "\n")

    print("Finished writing")


@router.post("/{section}/parse")
async def run_parse_route(
    section: InfoSources,
    indexing_is_needed: bool = True,
    parsing_is_needed: bool = False,
    saving_dump_is_needed: bool = False,
):  # dump used for generation and saving test data.
    if not indexing_is_needed and not parsing_is_needed:
        raise HTTPException(
            status_code=400, detail="At least one of indexing_is_needed or parsing_is_needed must be True"
        )

    if section == InfoSources.maps:
        parse_func, model_class = parse_maps, MapsEntry
    elif section == InfoSources.hotel:
        parse_func, model_class = parse_hotel, HotelEntry
    elif section == InfoSources.eduwiki:
        parse_func, model_class = parse_eduwiki, EduWikiEntry
    elif section == InfoSources.campuslife:
        parse_func, model_class = parse_campus_life, CampusLifeEntry
    elif section == InfoSources.residents:
        parse_func, model_class = parse_residents, ResidentsEntry
    elif section == InfoSources.resources:
        parse_func, model_class = load_resources, ResourcesEntry
    else:
        raise HTTPException(status_code=400, detail=f"Not supported section: {section}")
    all_entries: list[CustomDocument]
    if parsing_is_needed:
        to_create = parse_func()
        all_entries = []
        for entry in to_create:
            doc = model_class.model_validate(entry, from_attributes=True)
            all_entries.append(doc)

        if saving_dump_is_needed:
            # We were run to just generate files, so skip saving in db, return nothing
            save_dump(all_entries)
            return {}

        collection = model_class.get_motor_collection()
        await collection.delete_many({})
        for doc in all_entries:
            await doc.save()

        logger.info(f"{section} section entries parsed, {len(all_entries)} documents saved successfully.")

    else:
        collection = model_class.get_motor_collection()
        raw_entries = await collection.find().to_list(None)
        all_entries = [model_class.model_validate(entry) for entry in raw_entries]
        logger.info(f"Skip parsing, get entries from db for {section}")
    if indexing_is_needed:
        async with get_ml_service_client() as client:
            response = await client.post(
                f"/lancedb/update/{section.value}", json=[o.model_dump(mode="json") for o in all_entries], timeout=200
            )
            response.raise_for_status()
            response_data = response.json()
        return {"message": "success", "indexing": response_data, "parsing": all_entries}
    return {"message": "success", "indexing": None, "parsing": all_entries}
