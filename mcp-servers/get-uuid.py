import logging
import uuid
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp")
logger.setLevel(logging.WARNING)

mcp = FastMCP("uuid")

@mcp.tool()
async def get_uuid() -> str:
    """Get an uuid.
    """
    return str(uuid.uuid4())

if __name__ == "__main__":
    mcp.run(transport='stdio')
