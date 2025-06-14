"""Pydantic models for Claude Code transcript JSON structures."""

from typing import Any, List, Union, Optional, Dict, Literal
from pydantic import BaseModel


class TodoItem(BaseModel):
    id: str
    content: str
    status: Literal["pending", "in_progress", "completed"]
    priority: Literal["high", "medium", "low"]


class UsageInfo(BaseModel):
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    service_tier: str


class TextContent(BaseModel):
    type: Literal["text"]
    text: str


class ToolUseContent(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultContent(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str
    is_error: Optional[bool] = None


ContentItem = Union[TextContent, ToolUseContent, ToolResultContent]


class UserMessage(BaseModel):
    role: Literal["user"]
    content: Union[str, List[ContentItem]]


class AssistantMessage(BaseModel):
    id: str
    type: Literal["message"]
    role: Literal["assistant"]
    model: str
    content: List[ContentItem]
    stop_reason: Optional[str]
    stop_sequence: Optional[str]
    usage: UsageInfo


class FileInfo(BaseModel):
    filePath: str
    content: str
    numLines: int
    startLine: int
    totalLines: int


class FileReadResult(BaseModel):
    type: Literal["text"]
    file: FileInfo


class CommandResult(BaseModel):
    stdout: str
    stderr: str
    interrupted: bool
    isImage: bool


class TodoResult(BaseModel):
    oldTodos: List[TodoItem]
    newTodos: List[TodoItem]


class EditResult(BaseModel):
    oldString: Optional[str] = None
    newString: Optional[str] = None
    replaceAll: Optional[bool] = None
    originalFile: Optional[str] = None
    structuredPatch: Optional[Any] = None
    userModified: Optional[bool] = None


ToolUseResult = Union[str, FileReadResult, CommandResult, TodoResult, EditResult]


class BaseTranscriptEntry(BaseModel):
    parentUuid: Optional[str]
    isSidechain: bool
    userType: str
    cwd: str
    sessionId: str
    version: str
    uuid: str
    timestamp: str
    isMeta: Optional[bool] = None


class UserTranscriptEntry(BaseTranscriptEntry):
    type: Literal["user"]
    message: UserMessage
    toolUseResult: Optional[ToolUseResult] = None


class AssistantTranscriptEntry(BaseTranscriptEntry):
    type: Literal["assistant"]
    message: AssistantMessage
    requestId: str


class SummaryTranscriptEntry(BaseModel):
    type: Literal["summary"]
    summary: str
    leafUuid: str


TranscriptEntry = Union[
    UserTranscriptEntry, AssistantTranscriptEntry, SummaryTranscriptEntry
]


def parse_transcript_entry(data: Dict[str, Any]) -> TranscriptEntry:
    """
    Parse a JSON dictionary into the appropriate TranscriptEntry type.

    Args:
        data: Dictionary parsed from JSON

    Returns:
        The appropriate TranscriptEntry subclass

    Raises:
        ValueError: If the data doesn't match any known transcript entry type
    """
    entry_type = data.get("type")

    if entry_type == "user":
        return UserTranscriptEntry.model_validate(data)
    elif entry_type == "assistant":
        return AssistantTranscriptEntry.model_validate(data)
    elif entry_type == "summary":
        return SummaryTranscriptEntry.model_validate(data)
    else:
        raise ValueError(f"Unknown transcript entry type: {entry_type}")
