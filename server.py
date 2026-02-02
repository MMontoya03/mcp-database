import asyncio
import logging

from src.tools import mcp
from src.database import init_db, close_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Starting MCP Server...")
    
    # Inicializar base de datos
    asyncio.run(init_db())
    logger.info("Database initialized")
    
    # Ejecutar servidor
    mcp.run()