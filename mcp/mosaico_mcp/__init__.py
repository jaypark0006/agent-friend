"""Official Standard MCP Server for ESP-Mosaico (Agent Friend) 2.0."""

from .client import MosaicoClient
from .discovery import DeviceEndpoint, discover_device, utf8_clip
from .server import MosaicoMCPServer

__version__ = "2.0.0"

__all__ = [
    "__version__",
    "DeviceEndpoint",
    "MosaicoClient",
    "MosaicoMCPServer",
    "discover_device",
    "utf8_clip",
]
