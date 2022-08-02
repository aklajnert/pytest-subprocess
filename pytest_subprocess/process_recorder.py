from typing import Iterator
from typing import List
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from .types import COMMAND
from .utils import Command

if TYPE_CHECKING:
    from .fake_popen import FakePopen, AsyncFakePopen


class ProcessRecorder:
    """
    Recorder class that holds all FakePopen (or AsyncFakePopen) instances that were
    created by the subprocess. The class contains auxiliary
    """

    calls: List[Union["FakePopen", "AsyncFakePopen"]]

    def __init__(self) -> None:
        self.calls = []

    @property
    def first_call(self) -> Optional[Union["FakePopen", "AsyncFakePopen"]]:
        """Get the first process call"""
        if not self.calls:
            return None
        return self.calls[0]

    @property
    def last_call(self) -> Optional[Union["FakePopen", "AsyncFakePopen"]]:
        """Get the last (latest) process call"""
        if not self.calls:
            return None
        return self.calls[-1]

    def call_count(self, command: Optional[COMMAND] = None) -> int:
        """Get process call count - optionally match with arguments"""
        if not command:
            return len(self.calls)
        return len(tuple(self.get_matching_calls(command)))

    def was_called(self, command: Optional[COMMAND] = None) -> bool:
        """Check if process was called - optionally match with arguments"""
        if not self.calls:
            return False
        if not command:
            return True
        return any(self.get_matching_calls(command))

    def get_matching_calls(
        self, command: COMMAND
    ) -> Iterator[Union["FakePopen", "AsyncFakePopen"]]:
        """Get calls that match arguments"""
        if not isinstance(command, Command):
            command = Command(command)
        return (call for call in self.calls if self.calls if command == call.args)

    def clear(self) -> None:
        """Clear records"""
        self.calls.clear()
