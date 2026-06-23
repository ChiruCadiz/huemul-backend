from pydantic import BaseModel

class FileContext(BaseModel):
    filename: str
    content: str

class SessionContextRequest(BaseModel):
    files: list[FileContext]