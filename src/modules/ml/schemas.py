from src.custom_pydantic import CustomModel


# json with all info for vector db from backend
class SearchTask(CustomModel):
    ...


# json with all info for LLM from backend
class ChatTask(CustomModel):
    ...


# List of ranked sources/files to backend
class SearchResult(CustomModel):
    ...


# LLM answer to backend
class ChatResult(CustomModel):
    ...
