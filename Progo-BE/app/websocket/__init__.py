from .manager import ConnectionManager, websocket_manager

# Export the connection manager instance for use in other modules
connection_manager = websocket_manager

__all__ = ["ConnectionManager", "websocket_manager", "connection_manager"]