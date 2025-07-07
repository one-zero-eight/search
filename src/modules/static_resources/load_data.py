import yaml

from src.storages.mongo.innohassle import InNoHassleEntrySchema
from src.storages.mongo.myuni import MyUniEntrySchema


def load_entries_from_yaml(yaml_path: str, list_name: str, _MongoEntrySchema):
    with open(yaml_path) as file:
        data = yaml.safe_load(file)

    documents = []
    for entity in data.get(list_name, []):
        doc = {
            "source_url": entity["source_url"],
            "source_page_title": entity["source_page_title"],
            "content": entity["content"],
        }
        documents.append(_MongoEntrySchema(**doc))

    return documents


def load_myuni():
    return load_entries_from_yaml("./src/modules/static_resources/myuni.yaml", "myuni", MyUniEntrySchema)


def load_innohassle():
    return load_entries_from_yaml("./src/modules/static_resources/innohassle.yaml", "innohassle", InNoHassleEntrySchema)
