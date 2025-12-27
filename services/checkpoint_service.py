"""Checkpoint service for ETL incremental processing."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import structlog

from schemas.models import ETLCheckpoint
from core.database import get_db_session

logger = structlog.get_logger(__name__)


class CheckpointService:
    """Service for managing ETL checkpoints."""
    
    def __init__(self):
        pass
    
    def get_checkpoint(self, source: str, checkpoint_type: str) -> Optional[str]:
        """Get the latest checkpoint value for a source and type."""
        try:
            with get_db_session() as db:
                checkpoint = db.query(ETLCheckpoint).filter(
                    ETLCheckpoint.source == source,
                    ETLCheckpoint.checkpoint_type == checkpoint_type
                ).order_by(ETLCheckpoint.updated_at.desc()).first()
                
                if checkpoint:
                    logger.info(
                        "Retrieved checkpoint",
                        source=source,
                        checkpoint_type=checkpoint_type,
                        value=checkpoint.checkpoint_value
                    )
                    return checkpoint.checkpoint_value
                
                logger.info(
                    "No checkpoint found",
                    source=source,
                    checkpoint_type=checkpoint_type
                )
                return None
                
        except Exception as e:
            logger.error(
                "Failed to get checkpoint",
                source=source,
                checkpoint_type=checkpoint_type,
                error=str(e)
            )
            return None
    
    def set_checkpoint(
        self,
        source: str,
        checkpoint_type: str,
        checkpoint_value: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Set or update a checkpoint."""
        try:
            with get_db_session() as db:
                # Try to find existing checkpoint
                checkpoint = db.query(ETLCheckpoint).filter(
                    ETLCheckpoint.source == source,
                    ETLCheckpoint.checkpoint_type == checkpoint_type
                ).first()
                
                if checkpoint:
                    # Update existing checkpoint
                    checkpoint.checkpoint_value = checkpoint_value
                    checkpoint.metadata_json = metadata or {}
                    checkpoint.updated_at = datetime.utcnow()
                else:
                    # Create new checkpoint
                    checkpoint = ETLCheckpoint(
                        source=source,
                        checkpoint_type=checkpoint_type,
                        checkpoint_value=checkpoint_value,
                        metadata_json=metadata or {}
                    )
                    db.add(checkpoint)
                
                db.commit()
                
                logger.info(
                    "Checkpoint saved",
                    source=source,
                    checkpoint_type=checkpoint_type,
                    value=checkpoint_value
                )
                return True
                
        except Exception as e:
            logger.error(
                "Failed to set checkpoint",
                source=source,
                checkpoint_type=checkpoint_type,
                value=checkpoint_value,
                error=str(e)
            )
            return False
    
    def get_all_checkpoints(self, source: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """Get all checkpoints, optionally filtered by source."""
        try:
            with get_db_session() as db:
                query = db.query(ETLCheckpoint)
                if source:
                    query = query.filter(ETLCheckpoint.source == source)
                
                checkpoints = query.all()
                
                result = {}
                for checkpoint in checkpoints:
                    if checkpoint.source not in result:
                        result[checkpoint.source] = {}
                    result[checkpoint.source][checkpoint.checkpoint_type] = checkpoint.checkpoint_value
                
                return result
                
        except Exception as e:
            logger.error("Failed to get all checkpoints", error=str(e))
            return {}
    
    def clear_checkpoints(self, source: str) -> bool:
        """Clear all checkpoints for a source."""
        try:
            with get_db_session() as db:
                deleted = db.query(ETLCheckpoint).filter(
                    ETLCheckpoint.source == source
                ).delete()
                
                db.commit()
                
                logger.info(
                    "Checkpoints cleared",
                    source=source,
                    count=deleted
                )
                return True
                
        except Exception as e:
            logger.error(
                "Failed to clear checkpoints",
                source=source,
                error=str(e)
            )
            return False