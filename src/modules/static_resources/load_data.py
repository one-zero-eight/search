import yaml

from src.modules.resources_types_enum import Resources
from src.storages.mongo.resources import ResourcesEntrySchema


def load_entries_from_yaml(yaml_path: str, _MongoEntrySchema):
    with open(yaml_path, encoding="utf-8") as file:
        data = yaml.safe_load(file)

    documents = []
    for list_name, entries in data.items():
        try:
            resource_enum = Resources(list_name)
        except ValueError:
            print(f"⚠️ Missing unrecognized resource_type: {list_name}")
            continue

        for entity in entries:
            doc = {
                "source_url": entity["source_url"],
                "source_page_title": entity["source_page_title"],
                "content": entity["content"],
                "resource_type": resource_enum,
            }
            documents.append(_MongoEntrySchema(**doc))

    return documents


def load_resources():
    return load_entries_from_yaml("./src/modules/static_resources/resources.yaml", ResourcesEntrySchema)
