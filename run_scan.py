import asyncio
import logging
from services.collector import run_manual_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    asyncio.run(run_manual_scan())
