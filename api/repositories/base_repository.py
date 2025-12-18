"""
Base repository with common database operations.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Base repository class with common database operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db
