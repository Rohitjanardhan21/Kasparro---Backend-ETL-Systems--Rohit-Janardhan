"""Base class for data ingesters."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import structlog

from services.checkpoint_service import CheckpointService
from services.rate_limiter import RateLimiter, RateLimitConfig
from schemas.models import ETLRun
from core.database import get_db_session

logger = structlog.get_logger(__name__)


class BaseIngester(ABC):
    """Base class for all data ingesters."""
    
    def __init__(self, source_name: str, rate_limit_config: Optional[RateLimitConfig] = None):
        self.source_name = source_name
        self.checkpoint_service = CheckpointService()
        self.rate_limiter = RateLimiter(rate_limit_config) if rate_limit_config else None
        self.current_run_id = None
        self.current_run = None
    
    def start_run(self) -> str:
        """Start a new ETL run and return the run ID."""
        self.current_run_id = f"{self.source_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        try:
            with get_db_session() as db:
                self.current_run = ETLRun(
                    run_id=self.current_run_id,
                    source=self.source_name,
                    status="running",
                    start_time=datetime.utcnow(),
                    metadata_json={}
                )
                db.add(self.current_run)
                db.commit()
                
                logger.info(
                    "ETL run started",
                    run_id=self.current_run_id,
                    source=self.source_name
                )
                
        except Exception as e:
            logger.error(
                "Failed to start ETL run",
                source=self.source_name,
                error=str(e)
            )
            raise
        
        return self.current_run_id
    
    def update_run_stats(
        self,
        records_processed: int = 0,
        records_inserted: int = 0,
        records_updated: int = 0,
        records_failed: int = 0
    ) -> None:
        """Update run statistics."""
        if not self.current_run:
            return
        
        try:
            with get_db_session() as db:
                run = db.query(ETLRun).filter(ETLRun.run_id == self.current_run_id).first()
                if run:
                    run.records_processed += records_processed
                    run.records_inserted += records_inserted
                    run.records_updated += records_updated
                    run.records_failed += records_failed
                    db.commit()
                    
        except Exception as e:
            logger.error(
                "Failed to update run stats",
                run_id=self.current_run_id,
                error=str(e)
            )
    
    def complete_run(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Complete the current ETL run."""
        if not self.current_run:
            return
        
        try:
            with get_db_session() as db:
                run = db.query(ETLRun).filter(ETLRun.run_id == self.current_run_id).first()
                if run:
                    run.end_time = datetime.utcnow()
                    run.status = "completed" if success else "failed"
                    run.error_message = error_message
                    
                    if run.start_time and run.end_time:
                        run.duration_seconds = (run.end_time - run.start_time).total_seconds()
                    
                    db.commit()
                    
                    logger.info(
                        "ETL run completed",
                        run_id=self.current_run_id,
                        source=self.source_name,
                        status=run.status,
                        duration_seconds=run.duration_seconds,
                        records_processed=run.records_processed
                    )
                    
        except Exception as e:
            logger.error(
                "Failed to complete ETL run",
                run_id=self.current_run_id,
                error=str(e)
            )
        finally:
            self.current_run = None
            self.current_run_id = None
    
    @abstractmethod
    def extract_data(self) -> List[Dict[str, Any]]:
        """Extract data from the source."""
        pass
    
    @abstractmethod
    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw data into normalized format."""
        pass
    
    @abstractmethod
    def load_data(self, transformed_data: List[Dict[str, Any]]) -> int:
        """Load transformed data into the database."""
        pass
    
    def run(self) -> Dict[str, Any]:
        """Run the complete ETL process."""
        run_id = self.start_run()
        
        try:
            # Extract
            logger.info("Starting data extraction", source=self.source_name)
            raw_data = self.extract_data()
            logger.info(
                "Data extraction completed",
                source=self.source_name,
                records_extracted=len(raw_data)
            )
            
            if not raw_data:
                logger.info("No new data to process", source=self.source_name)
                self.complete_run(success=True)
                return {
                    "run_id": run_id,
                    "status": "completed",
                    "records_processed": 0,
                    "message": "No new data to process"
                }
            
            # Transform
            logger.info("Starting data transformation", source=self.source_name)
            transformed_data = self.transform_data(raw_data)
            logger.info(
                "Data transformation completed",
                source=self.source_name,
                records_transformed=len(transformed_data)
            )
            
            # Load
            logger.info("Starting data loading", source=self.source_name)
            records_loaded = self.load_data(transformed_data)
            logger.info(
                "Data loading completed",
                source=self.source_name,
                records_loaded=records_loaded
            )
            
            self.update_run_stats(
                records_processed=len(raw_data),
                records_inserted=records_loaded
            )
            
            self.complete_run(success=True)
            
            return {
                "run_id": run_id,
                "status": "completed",
                "records_processed": len(raw_data),
                "records_loaded": records_loaded
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "ETL run failed",
                source=self.source_name,
                run_id=run_id,
                error=error_msg
            )
            
            self.complete_run(success=False, error_message=error_msg)
            
            return {
                "run_id": run_id,
                "status": "failed",
                "error": error_msg
            }