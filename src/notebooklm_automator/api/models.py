from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class SourceType(str, Enum):
    URL = "url"
    YOUTUBE = "youtube"
    TEXT = "text"


class Source(BaseModel):
    type: SourceType
    content: str  # URL or text content


class UploadSourcesRequest(BaseModel):
    sources: List[Source]


class SourceResult(BaseModel):
    source: Source
    success: bool
    error: Optional[str] = None


class UploadResponse(BaseModel):
    overall_success: bool
    results: List[SourceResult]


class AudioStyle(str, Enum):
    # Based on standard NotebookLM styles (simplified mapping)
    SUMMARY = "summary"
    DEEP_DIVE = "deep_dive"  # Default conversation
    CRITICISM = "criticism"
    DEBATE = "debate"


class AudioDuration(str, Enum):
    SHORT = "short"
    DEFAULT = "default"


class GenerateAudioRequest(BaseModel):
    style: Optional[AudioStyle] = None
    prompt: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[AudioDuration] = None


class GenerateAudioResponse(BaseModel):
    job_id: str
    status: str


class AudioStatusResponse(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    title: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


class ClearSourcesResponse(BaseModel):
    success: bool
    count: int
    message: Optional[str] = None


class ClearStudioResponse(BaseModel):
    success: bool
    count: int
    message: Optional[str] = None
