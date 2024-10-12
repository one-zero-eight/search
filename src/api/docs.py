import re

from fastapi.routing import APIRoute

# API version
VERSION = "0.1.0"

# Info for OpenAPI specification
TITLE = "InNoHassle Search API"
SUMMARY = "Search service for InNoHassle ecosystem."

DESCRIPTION = """
### About this project

This is the API for Search project in InNoHassle ecosystem developed by one-zero-eight community.

Using this API you can search among Moodle documents.

Backend is developed using FastAPI framework on Python.

Note: API is unstable. Endpoints and models may change in the future.

Useful links:
- [Search API source code](https://github.com/one-zero-eight/search)
- [Search ML Experiments source code](https://github.com/one-zero-eight/search-experiments)
- [InNoHassle Website](https://innohassle.ru/)
"""

CONTACT_INFO = {
    "name": "one-zero-eight (Telegram)",
    "url": "https://t.me/one_zero_eight",
}

LICENSE_INFO = {
    "name": "MIT License",
    "identifier": "MIT",
}


def generate_unique_operation_id(route: APIRoute) -> str:
    # Better names for operationId in OpenAPI schema.
    # It is needed because clients generate code based on these names.
    # Requires pair (tag name + function name) to be unique.
    # See fastapi.utils:generate_unique_id (default implementation).
    if route.tags:
        operation_id = f"{route.tags[0]}_{route.name}".lower()
    else:
        operation_id = route.name.lower()
    operation_id = re.sub(r"\W+", "_", operation_id)
    return operation_id
