"""Typed execution operations and replaceable backends."""

from .contracts import ExecutionBackend, ExecutionControl, FileReadRequest, FileReadResult
from .local import LocalExecutionBackend

__all__ = [
    "ExecutionBackend",
    "ExecutionControl",
    "FileReadRequest",
    "FileReadResult",
    "LocalExecutionBackend",
]
