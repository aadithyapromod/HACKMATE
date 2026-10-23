from typing import List, Optional
from pydantic import BaseModel, Field


class GeneratedFile(BaseModel):
    path: str = Field(..., example="src/App.jsx")
    content: str = Field(..., example="export default function App() { return <h1>Hello</h1>; }")


class FileListResponse(BaseModel):
    files: List[GeneratedFile] = Field(default_factory=list)


class BuildResult(BaseModel):
    success: bool = Field(..., example=True)
    exit_code: int = Field(..., example=0)
    logs: str = Field(..., example="Build succeeded")
    preview_url: Optional[str] = Field(default=None, example=None)
