"""Statistics endpoint for ETL run information."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timedelta
import structlog

from core.database import get_db
from schemas.models import ETLRun, NormalizedCryptoData
from schemas.pydantic_models import StatsResponse, ETLRunResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """
    Get ETL statistics and summaries.
    
    Returns comprehensive statistics about ETL runs including:
    - Total and successful/failed run counts
    - Last successful and failed runs
    - Records processed by source
    - Average run duration
    """
    try:
        # Get total run counts
        total_runs = db.query(func.count(ETLRun.id)).scalar() or 0
        successful_runs = db.query(func.count(ETLRun.id)).filter(ETLRun.status == "completed").scalar() or 0
        failed_runs = db.query(func.count(ETLRun.id)).filter(ETLRun.status == "failed").scalar() or 0
        
        # Get last successful run
        last_successful_run = None
        last_successful = db.query(ETLRun).filter(
            ETLRun.status == "completed"
        ).order_by(desc(ETLRun.end_time)).first()
        
        if last_successful:
            last_successful_run = {
                "run_id": last_successful.run_id,
                "source": last_successful.source,
                "end_time": last_successful.end_time.isoformat() if last_successful.end_time else None,
                "duration_seconds": last_successful.duration_seconds,
                "records_processed": last_successful.records_processed
            }
        
        # Get last failed run
        last_failed_run = None
        last_failed = db.query(ETLRun).filter(
            ETLRun.status == "failed"
        ).order_by(desc(ETLRun.start_time)).first()
        
        if last_failed:
            last_failed_run = {
                "run_id": last_failed.run_id,
                "source": last_failed.source,
                "start_time": last_failed.start_time.isoformat(),
                "error_message": last_failed.error_message
            }
        
        # Get records by source
        records_by_source = {}
        source_counts = db.query(
            NormalizedCryptoData.source,
            func.count(NormalizedCryptoData.id).label('count')
        ).group_by(NormalizedCryptoData.source).all()
        
        for row in source_counts:
            records_by_source[row.source] = row.count
        
        # Get average duration
        avg_duration = db.query(
            func.avg(ETLRun.duration_seconds)
        ).filter(
            ETLRun.status == "completed",
            ETLRun.duration_seconds.isnot(None)
        ).scalar()
        
        response = StatsResponse(
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            last_successful_run=last_successful_run,
            last_failed_run=last_failed_run,
            records_by_source=records_by_source,
            avg_duration_seconds=float(avg_duration) if avg_duration else None
        )
        
        logger.info(
            "Stats request completed",
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs
        )
        
        return response
        
    except Exception as e:
        logger.error("Stats request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/runs", response_model=List[ETLRunResponse])
async def get_etl_runs(
    limit: int = Query(50, ge=1, le=1000, description="Number of runs to return"),
    source: Optional[str] = Query(None, description="Filter by source"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about ETL runs.
    
    Returns a list of ETL runs with filtering options.
    """
    try:
        # Build query
        query = db.query(ETLRun)
        
        # Apply filters
        if source:
            query = query.filter(ETLRun.source == source)
        
        if status:
            if status not in ["running", "completed", "failed"]:
                raise HTTPException(status_code=400, detail="Invalid status. Must be: running, completed, or failed")
            query = query.filter(ETLRun.status == status)
        
        # Get runs ordered by start time (most recent first)
        runs = query.order_by(desc(ETLRun.start_time)).limit(limit).all()
        
        # Convert to response models
        response = [ETLRunResponse.from_orm(run) for run in runs]
        
        logger.info(
            "ETL runs request completed",
            runs_returned=len(response),
            source_filter=source,
            status_filter=status
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ETL runs request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/performance")
async def get_performance_stats(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    db: Session = Depends(get_db)
):
    """
    Get performance statistics for the specified time window.
    
    Returns performance metrics including throughput, success rates, and trends.
    """
    try:
        # Calculate time window
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get runs in time window
        runs = db.query(ETLRun).filter(ETLRun.start_time >= cutoff_time).all()
        
        if not runs:
            return {
                "time_window_hours": hours,
                "message": f"No ETL runs found in the last {hours} hours",
                "stats": {}
            }
        
        # Calculate statistics
        total_runs = len(runs)
        successful_runs = [r for r in runs if r.status == "completed"]
        failed_runs = [r for r in runs if r.status == "failed"]
        running_runs = [r for r in runs if r.status == "running"]
        
        # Performance metrics
        total_records_processed = sum(r.records_processed for r in runs)
        avg_records_per_run = total_records_processed / total_runs if total_runs > 0 else 0
        
        # Duration statistics (only for completed runs)
        completed_with_duration = [r for r in successful_runs if r.duration_seconds is not None]
        avg_duration = sum(r.duration_seconds for r in completed_with_duration) / len(completed_with_duration) if completed_with_duration else None
        min_duration = min(r.duration_seconds for r in completed_with_duration) if completed_with_duration else None
        max_duration = max(r.duration_seconds for r in completed_with_duration) if completed_with_duration else None
        
        # Throughput (records per hour)
        throughput_per_hour = total_records_processed / hours if hours > 0 else 0
        
        # Success rate
        success_rate = len(successful_runs) / total_runs if total_runs > 0 else 0
        
        # By source breakdown
        by_source = {}
        for source in set(r.source for r in runs):
            source_runs = [r for r in runs if r.source == source]
            source_successful = [r for r in source_runs if r.status == "completed"]
            
            by_source[source] = {
                "total_runs": len(source_runs),
                "successful_runs": len(source_successful),
                "success_rate": len(source_successful) / len(source_runs) if source_runs else 0,
                "total_records": sum(r.records_processed for r in source_runs),
                "avg_records_per_run": sum(r.records_processed for r in source_runs) / len(source_runs) if source_runs else 0
            }
        
        response = {
            "time_window_hours": hours,
            "period_start": cutoff_time.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "summary": {
                "total_runs": total_runs,
                "successful_runs": len(successful_runs),
                "failed_runs": len(failed_runs),
                "running_runs": len(running_runs),
                "success_rate": round(success_rate, 4),
                "total_records_processed": total_records_processed,
                "avg_records_per_run": round(avg_records_per_run, 2),
                "throughput_records_per_hour": round(throughput_per_hour, 2)
            },
            "duration_stats": {
                "avg_duration_seconds": round(avg_duration, 2) if avg_duration else None,
                "min_duration_seconds": round(min_duration, 2) if min_duration else None,
                "max_duration_seconds": round(max_duration, 2) if max_duration else None,
                "completed_runs_with_duration": len(completed_with_duration)
            },
            "by_source": by_source
        }
        
        logger.info(
            "Performance stats request completed",
            time_window_hours=hours,
            total_runs=total_runs,
            success_rate=success_rate
        )
        
        return response
        
    except Exception as e:
        logger.error("Performance stats request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")