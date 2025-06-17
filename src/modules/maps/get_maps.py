import requests

response = requests.get("https://api.innohassle.ru/maps/v0/scenes/").json()

with open("maps.md", "a", encoding="utf-8") as areas_f:
    for scene in response:
        areas_f.write(f"# {scene["title"]}\n")
        for area in scene["areas"]:
            areas_f.write(f"### {area["title"]}\n")
            if area["description"]:
                areas_f.write(f"**Description:** {"  \n".join(area["description"].split("\n"))}  \n")
            areas_f.write(
                f"**Link:** https://innohassle.ru/maps?scene={scene['scene_id']}&area={area['svg_polygon_id']}  \n"
            )
            if area["people"]:
                areas_f.write("**People:** ")
                areas_f.write(f"{', '.join(area["people"][::2])}  \n")
