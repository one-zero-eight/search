import yaml

from src.storages.mongo.resources import ResourcesEntrySchema


def load_entries_from_yaml(yaml_path: str, list_names: str, _MongoEntrySchema):
    with open(yaml_path) as file:
        data = yaml.safe_load(file)

    documents = []
    for list_name in list_names:
        for entity in data.get(list_name, []):
            doc = {
                "source_url": entity["source_url"],
                "source_page_title": entity["source_page_title"],
                "content": entity["content"],
            }
            documents.append(_MongoEntrySchema(**doc))

    return documents


def load_resources():
    return load_entries_from_yaml(
        "./src/modules/static_resources/resources.yaml", ["myuni", "innohassle"], ResourcesEntrySchema
    )
