"""
Import history repository for database operations.
"""
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.domain import ImportHistory
from api.repositories.base_repository import BaseRepository


class ImportRepository(BaseRepository):
    """Repository for import history database operations."""
    
    async def create_import_history(
        self,
        user_id: str,
        import_type: str,
        account_id: str,
        filename: Optional[str],
        rows_total: int,
        rows_inserted: int,
        rows_skipped: int,
        status: str,
        error_message: Optional[str] = None
    ) -> ImportHistory:
        """
        Create a new import history record.
        
        Args:
            user_id: User ID who performed the import
            import_type: Type of import ('credit_card' or 'bank')
            account_id: Account ID for the transactions
            filename: Original filename (optional)
            rows_total: Total rows in the CSV
            rows_inserted: Number of rows successfully inserted
            rows_skipped: Number of rows skipped (duplicates or errors)
            status: Import status ('success', 'failed', 'partial')
            error_message: Error message if import failed
            
        Returns:
            Created ImportHistory record
        """
        import_history = ImportHistory(
            user_id=user_id,
            import_type=import_type,
            account_id=account_id,
            filename=filename,
            rows_total=rows_total,
            rows_inserted=rows_inserted,
            rows_skipped=rows_skipped,
            status=status,
            error_message=error_message
        )
        
        self.db.add(import_history)
        await self.db.commit()
        await self.db.refresh(import_history)
        
        return import_history
    
    async def get_import_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[ImportHistory], int]:
        """
        Get import history for a user.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            Tuple of (list of import history records, total count)
        """
        # Build query
        query = select(ImportHistory).where(
            ImportHistory.user_id == user_id
        ).order_by(desc(ImportHistory.created_at))
        
        # Get total count
        count_query = select(ImportHistory).where(
            ImportHistory.user_id == user_id
        )
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await self.db.execute(query)
        imports = result.scalars().all()
        
        return list(imports), total
    
    async def get_import_by_id(
        self,
        import_id: str,
        user_id: str
    ) -> Optional[ImportHistory]:
        """
        Get a single import history record by ID, ensuring it belongs to the user.
        
        Args:
            import_id: Import ID
            user_id: User ID to verify ownership
            
        Returns:
            ImportHistory record if found and belongs to user, None otherwise
        """
        query = select(ImportHistory).where(
            ImportHistory.import_id == import_id,
            ImportHistory.user_id == user_id
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


