import datetime
import logging
from zoneinfo import ZoneInfo
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp")
logger.setLevel(logging.WARNING)

mcp = FastMCP("datetime")

@mcp.tool()
async def get_datetime(timezone: str | None = None) -> str:
    """Get a datetime.
    Args:
        timezone (str | None): The timezone to use. If None, use the local timezone.
    Returns:
        str: The current datetime in the specified timezone.
    """
    #dt_now = datetime.datetime.now(ZoneInfo('Asia/Tokyo'))
    #dt_now = datetime.datetime.now(ZoneInfo('Europe/London'))
    if timezone:
       dt_now = datetime.datetime.now(ZoneInfo(timezone))
    else:
        dt_now = datetime.datetime.now()
    return dt_now.strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    mcp.run(transport='stdio')
