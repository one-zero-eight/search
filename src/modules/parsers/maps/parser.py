import requests

from src.storages.mongo.maps import MapsEntrySchema


def parse():
    result = []
    response = requests.get("https://api.innohassle.ru/maps/v0/scenes/").json()

    for scene in response:
        scene_str = f"# {scene['title']}\n"
        preposition = "on" if scene["title"].lower().startswith("floor") else "in"
        for area in scene["areas"]:
            area_str = f"### {area['title']}\n"
            description_str = ""
            if area["description"]:
                joined_lines = "  \n".join(area["description"].split("\n"))
                description_str = f"**Description:** {joined_lines}  \n"
            link_str = f"https://innohassle.ru/maps?scene={scene['scene_id']}&area={area['svg_polygon_id']}"
            people_str = ""
            if area["people"]:
                people_str = "**People:** "
                people_str += f"{', '.join(area['people'][::2])}  \n"
            content = scene_str + area_str + description_str + people_str
            result.append(
                MapsEntrySchema(
                    location_url=link_str,
                    scene_id=scene["scene_id"],
                    area_id=area["svg_polygon_id"],
                    content=content,
                    title=f"Maps: {area['title']} {preposition} {scene['title']}",
                )
            )
    return result
