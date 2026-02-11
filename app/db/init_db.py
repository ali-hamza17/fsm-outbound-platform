"""
Initialize database tables
Run this once to create tables
"""

import asyncio
import sys
from pathlib import Path

# Add the db directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db


if __name__ == "__main__":
    print("Creating database tables...")
    asyncio.run(init_db())