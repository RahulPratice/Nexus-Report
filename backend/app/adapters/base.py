from abc import ABC, abstractmethod
from app.models.utrs import TestRun


class BaseAdapter(ABC):
    """
    Every testing tool adapter inherits from this.
    The only requirement: implement parse() to return a TestRun.
    """

    tool_name: str = "unknown"

    @abstractmethod
    def parse(self, raw_data: dict) -> TestRun:
        """
        Parse the native output of a testing tool into a Unified TestRun.
        raw_data: the JSON body sent to /api/v1/ingest
        returns: a fully populated TestRun instance
        """
        ...

    def _safe_get(self, d: dict, *keys, default=None):
        """Safely traverse nested dict keys."""
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key, default)
            else:
                return default
        return d


ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {}


def register_adapter(tool_name: str):
    """Decorator to register adapters by tool name."""
    def decorator(cls: type[BaseAdapter]):
        ADAPTER_REGISTRY[tool_name] = cls
        cls.tool_name = tool_name
        return cls
    return decorator


def get_adapter(tool_name: str) -> BaseAdapter:
    if tool_name not in ADAPTER_REGISTRY:
        raise ValueError(
            f"No adapter registered for tool '{tool_name}'. "
            f"Available: {list(ADAPTER_REGISTRY.keys())}"
        )
    return ADAPTER_REGISTRY[tool_name]()
