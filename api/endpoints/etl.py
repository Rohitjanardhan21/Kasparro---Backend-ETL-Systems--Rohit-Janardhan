"""ETL management endpoints."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import asyncio
import subprocess
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["ETL Management"])

@router.post("/etl/run")
async def trigger_etl(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Trigger ETL process manually.
    
    Returns:
        Dict containing ETL trigger status and run ID
    """
    try:
        run_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add ETL task to background
        background_tasks.add_task(run_etl_process, run_id)
        
        logger.info("ETL process triggered manually", run_id=run_id)
        
        return {
            "status": "triggered",
            "run_id": run_id,
            "message": "ETL process started in background",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to trigger ETL process", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger ETL process: {str(e)}"
        )

@router.get("/etl/status")
async def get_etl_status() -> Dict[str, Any]:
    """
    Get current ETL process status.
    
    Returns:
        Dict containing ETL status information
    """
    try:
        # Check if ETL process is running
        result = subprocess.run(
            ["pgrep", "-f", "ingestion.main"],
            capture_output=True,
            text=True
        )
        
        is_running = result.returncode == 0
        
        return {
            "etl_running": is_running,
            "timestamp": datetime.now().isoformat(),
            "message": "ETL process is running" if is_running else "ETL process is not running"
        }
        
    except Exception as e:
        logger.error("Failed to check ETL status", error=str(e))
        return {
            "etl_running": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

async def run_etl_process(run_id: str):
    """
    Run ETL process in background.
    
    Args:
        run_id: Unique identifier for this ETL run
    """
    try:
        logger.info("Starting ETL process", run_id=run_id)
        
        # Run ETL process
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "ingestion.main",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("ETL process completed successfully", 
                       run_id=run_id, 
                       stdout=stdout.decode())
        else:
            logger.error("ETL process failed", 
                        run_id=run_id, 
                        stderr=stderr.decode())
            
    except Exception as e:
        logger.error("ETL process execution failed", 
                    run_id=run_id, 
                    error=str(e))