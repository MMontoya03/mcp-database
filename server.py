#servidor MCP que expone las tools al modelo
import logging
from src.tools import mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting MCP Server...")
    mcp.run()
