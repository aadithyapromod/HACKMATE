from typing import List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FileMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_path: str
    language: str
    file_size_bytes: int
    version: int
    updated_at: datetime


class FileDetailResponse(FileMetadataResponse):
    content: str


class FileListResponse(BaseModel):
    project_id: str
    total_files: int
    files: List[FileMetadataResponse]
