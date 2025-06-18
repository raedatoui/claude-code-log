"""Pydantic models for Claude Code transcript JSON structures."""

from typing import Any, List, Union, Optional, Dict, Literal, cast
from pydantic import BaseModel


class TodoItem(BaseModel):
    id: str
    content: str
    status: Literal["pending", "in_progress", "completed"]
    priority: Literal["high", "medium", "low"]


class UsageInfo(BaseModel):
    input_tokens: int
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None
    output_tokens: int
    service_tier: Optional[str] = None


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
    content: Union[str, List[Dict[str, Any]]]
    is_error: Optional[bool] = None


class ThinkingContent(BaseModel):
    type: Literal["thinking"]
    thinking: str
    signature: Optional[str] = None


class ImageSource(BaseModel):
    type: Literal["base64"]
    media_type: str
    data: str


class ImageContent(BaseModel):
    type: Literal["image"]
    source: ImageSource


ContentItem = Union[
    TextContent, ToolUseContent, ToolResultContent, ThinkingContent, ImageContent
]


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
    usage: Optional[UsageInfo] = None


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
    requestId: Optional[str] = None


class SummaryTranscriptEntry(BaseModel):
    type: Literal["summary"]
    summary: str
    leafUuid: str


TranscriptEntry = Union[
    UserTranscriptEntry, AssistantTranscriptEntry, SummaryTranscriptEntry
]


def parse_content_item(item_data: Dict[str, Any]) -> ContentItem:
    """Parse a content item based on its type field."""
    try:
        content_type = item_data.get("type", "")

        if content_type == "text":
            return TextContent.model_validate(item_data)
        elif content_type == "tool_use":
            return ToolUseContent.model_validate(item_data)
        elif content_type == "tool_result":
            return ToolResultContent.model_validate(item_data)
        elif content_type == "thinking":
            return ThinkingContent.model_validate(item_data)
        elif content_type == "image":
            return ImageContent.model_validate(item_data)
        else:
            # Fallback to text content for unknown types
            return TextContent(type="text", text=str(item_data))
    except AttributeError:
        return TextContent(type="text", text=str(item_data))


def parse_message_content(content_data: Any) -> Union[str, List[ContentItem]]:
    """Parse message content, handling both string and list formats."""
    if isinstance(content_data, str):
        return content_data
    elif isinstance(content_data, list):
        content_list = cast(List[Dict[str, Any]], content_data)
        return [parse_content_item(item) for item in content_list]
    else:
        return str(content_data)


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
        # Parse message content if present
        data_copy = data.copy()
        if "message" in data_copy and "content" in data_copy["message"]:
            data_copy["message"] = data_copy["message"].copy()
            data_copy["message"]["content"] = parse_message_content(
                data_copy["message"]["content"]
            )
        return UserTranscriptEntry.model_validate(data_copy)
    elif entry_type == "assistant":
        # Parse message content if present
        data_copy = data.copy()
        if "message" in data_copy and "content" in data_copy["message"]:
            data_copy["message"] = data_copy["message"].copy()
            data_copy["message"]["content"] = parse_message_content(
                data_copy["message"]["content"]
            )
        return AssistantTranscriptEntry.model_validate(data_copy)
    elif entry_type == "summary":
        return SummaryTranscriptEntry.model_validate(data)
    else:
        raise ValueError(f"Unknown transcript entry type: {entry_type}")
