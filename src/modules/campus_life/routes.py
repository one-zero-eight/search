from fastapi import APIRouter, HTTPException

from src.storages.mongo.campus_life import CampusLifeEntry

from .clubs import parse as parse_clubs
from .handbook import parse as parse_handbook

router = APIRouter()


@router.post("/campus-life/parse")
async def upload_markdown_file():
    try:
        await CampusLifeEntry.get_motor_collection().delete_many({})

        clubs_data = parse_clubs()
        handbook_data = {"handbook2023.md": parse_handbook()}

        all_entries = {**clubs_data, **handbook_data}

        for entry in all_entries.values():
            doc = CampusLifeEntry.model_validate(entry, from_attributes=True)
            await doc.save()

        return {"message": f"{len(all_entries)} documents saved successfully.", "entries": all_entries}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during parsing or saving: {e}")
