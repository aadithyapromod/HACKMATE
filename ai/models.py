from typing import List, Literal
from pydantic import BaseModel, Field


class PlanTask(BaseModel):
    id: str = Field(..., example="task-1")
    title: str = Field(..., example="Generate application files")
    description: str = Field(..., example="Generate the React application source")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending"
    )


class PlanOutput(BaseModel):
    summary: str = Field(..., description="High level summary of the architecture")
    framework: Literal["react-vite"] = Field(
        default="react-vite",
        description="Target framework for HackMate MVP (React + Vite only)"
    )
    tasks: List[PlanTask] = Field(default_factory=list)


class GeneratedFileModel(BaseModel):
    path: str = Field(..., example="src/App.jsx")
    content: str = Field(..., example="export default function App() { return <h1>Hello</h1>; }")


class FileListOutput(BaseModel):
    files: List[GeneratedFileModel] = Field(default_factory=list)
