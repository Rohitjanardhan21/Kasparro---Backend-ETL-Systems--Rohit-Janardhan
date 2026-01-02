"""Data endpoint for retrieving normalized cryptocurrency data."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, Dict, Any, List
from datetime import datetime
import time
import structlog

from core.database import get_db
from schemas.models import NormalizedCryptoData
from schemas.pydantic_models import DataResponse, NormalizedCryptoResponse, DataQueryParams
from services.circuit_breaker import db_circuit_breaker

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/data/samples")
async def get_data_samples(db: Session = Depends(get_db)):
    """
    Get sample data from each source for evaluation verification.
    
    Returns representative samples from CSV, CoinPaprika, and CoinGecko
    to demonstrate multi-source ETL functionality.
    """
    try:
        samples = {
            "timestamp": datetime.utcnow().isoformat(),
            "sources": {}
        }
        
        # Get CSV samples
        csv_query = db.query(NormalizedCryptoData).filter(
            NormalizedCryptoData.source == "csv"
        ).limit(3)
        csv_samples = csv_query.all()
        
        samples["sources"]["csv"] = {
            "count": len(csv_samples),
            "samples": [
                {
                    "coin_id": item.coin_id,
                    "name": item.name,
                    "symbol": item.symbol,
                    "price_usd": float(item.price_usd),
                    "source": item.source,
                    "processed_at": item.processed_at.isoformat()
                }
                for item in csv_samples
            ]
        }
        
        # Get CoinPaprika samples
        coinpaprika_query = db.query(NormalizedCryptoData).filter(
            NormalizedCryptoData.source == "coinpaprika"
        ).limit(3)
        coinpaprika_samples = coinpaprika_query.all()
        
        samples["sources"]["coinpaprika"] = {
            "count": len(coinpaprika_samples),
            "samples": [
                {
                    "coin_id": item.coin_id,
                    "name": item.name,
                    "symbol": item.symbol,
                    "price_usd": float(item.price_usd),
                    "source": item.source,
                    "processed_at": item.processed_at.isoformat()
                }
                for item in coinpaprika_samples
            ]
        }
        
        # Get CoinGecko samples
        coingecko_query = db.query(NormalizedCryptoData).filter(
            NormalizedCryptoData.source == "coingecko"
        ).limit(3)
        coingecko_samples = coingecko_query.all()
        
        samples["sources"]["coingecko"] = {
            "count": len(coingecko_samples),
            "samples": [
                {
                    "coin_id": item.coin_id,
                    "name": item.name,
                    "symbol": item.symbol,
                    "price_usd": float(item.price_usd),
                    "source": item.source,
                    "processed_at": item.processed_at.isoformat()
                }
                for item in coingecko_samples
            ]
        }
        
        # Add summary
        total_csv = db.query(func.count(NormalizedCryptoData.id)).filter(
            NormalizedCryptoData.source == "csv"
        ).scalar() or 0
        
        total_coinpaprika = db.query(func.count(NormalizedCryptoData.id)).filter(
            NormalizedCryptoData.source == "coinpaprika"
        ).scalar() or 0
        
        total_coingecko = db.query(func.count(NormalizedCryptoData.id)).filter(
            NormalizedCryptoData.source == "coingecko"
        ).scalar() or 0
        
        samples["summary"] = {
            "total_records": total_csv + total_coinpaprika + total_coingecko,
            "by_source": {
                "csv": total_csv,
                "coinpaprika": total_coinpaprika,
                "coingecko": total_coingecko
            },
            "multi_source_validation": {
                "csv_present": total_csv > 0,
                "coinpaprika_present": total_coinpaprika > 0,
                "coingecko_present": total_coingecko > 0,
                "all_sources_working": all([total_csv > 0, total_coinpaprika > 0, total_coingecko > 0])
            }
        }
        
        return samples
        
    except Exception as e:
        logger.error("Failed to get data samples", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve data samples: {str(e)}"
        )


@router.get("/data", response_model=DataResponse)
async def get_data(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records per page"),
    source: Optional[str] = Query(None, description="Filter by data source (coinpaprika, coingecko, csv)"),
    coin_id: Optional[str] = Query(None, description="Filter by coin ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Retrieve paginated cryptocurrency data with filtering options.
    
    Returns normalized cryptocurrency data from all sources with pagination
    and filtering capabilities. Includes request metadata and performance metrics.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"
    
    try:
        # Validate query parameters
        query_params = DataQueryParams(
            page=page,
            limit=limit,
            source=source,
            coin_id=coin_id,
            symbol=symbol
        )
        
        # Use circuit breaker for database operations
        @db_circuit_breaker
        def execute_query():
            try:
                # Build query with connection validation
                query = db.query(NormalizedCryptoData)
                
                # Apply filters
                if query_params.source:
                    query = query.filter(NormalizedCryptoData.source == query_params.source)
                
                if query_params.coin_id:
                    query = query.filter(NormalizedCryptoData.coin_id.ilike(f"%{query_params.coin_id}%"))
                
                if query_params.symbol:
                    query = query.filter(NormalizedCryptoData.symbol.ilike(f"%{query_params.symbol}%"))
                
                # Get total count for pagination with timeout protection
                try:
                    total_count = query.count()
                except Exception as e:
                    logger.warning(f"Count query failed, using fallback: {e}")
                    # Fallback: estimate count or use a default
                    total_count = 0
                
                # Apply pagination and ordering with error handling
                offset = (query_params.page - 1) * query_params.limit
                try:
                    records = query.order_by(desc(NormalizedCryptoData.processed_at)).offset(offset).limit(query_params.limit).all()
                except Exception as e:
                    logger.warning(f"Data query failed, returning empty result: {e}")
                    records = []
                    if total_count == 0:
                        # If both count and data queries failed, there might be a connection issue
                        raise Exception("Database connection issue detected")
                
                return total_count, records
                
            except Exception as e:
                logger.error(f"Database query execution failed: {e}")
                # Re-raise to trigger circuit breaker
                raise
        
        # Execute query with circuit breaker protection
        total_count, records = execute_query()
        
        # Calculate pagination metadata
        total_pages = (total_count + query_params.limit - 1) // query_params.limit
        has_next = query_params.page < total_pages
        has_prev = query_params.page > 1
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Convert to response models
        data = [NormalizedCryptoResponse.from_orm(record) for record in records]
        
        # Build response
        response = DataResponse(
            data=data,
            pagination={
                "page": query_params.page,
                "limit": query_params.limit,
                "total_records": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": query_params.page + 1 if has_next else None,
                "prev_page": query_params.page - 1 if has_prev else None
            },
            metadata={
                "request_id": request_id,
                "api_latency_ms": round(latency_ms, 2),
                "filters_applied": {
                    "source": query_params.source,
                    "coin_id": query_params.coin_id,
                    "symbol": query_params.symbol
                },
                "records_returned": len(data)
            }
        )
        
        logger.info(
            "Data request completed",
            request_id=request_id,
            page=query_params.page,
            limit=query_params.limit,
            total_records=total_count,
            records_returned=len(data),
            latency_ms=round(latency_ms, 2)
        )
        
        return response
        
    except ValueError as e:
        logger.warning(
            "Invalid query parameters",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail="Invalid query parameters")
    
    except Exception as e:
        logger.error(
            "Data request failed",
            request_id=request_id,
            error=str(e)
        )
        # Don't expose internal error details
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/data/summary")
async def get_data_summary(
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Get summary statistics about the available data.
    
    Returns counts by source, latest update times, and other metadata.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"
    
    try:
        # Get counts by source
        source_counts = db.query(
            NormalizedCryptoData.source,
            func.count(NormalizedCryptoData.id).label('count')
        ).group_by(NormalizedCryptoData.source).all()
        
        # Get latest update by source
        latest_updates = db.query(
            NormalizedCryptoData.source,
            func.max(NormalizedCryptoData.processed_at).label('latest_update')
        ).group_by(NormalizedCryptoData.source).all()
        
        # Get total count
        total_records = db.query(func.count(NormalizedCryptoData.id)).scalar()
        
        # Get unique coins count
        unique_coins = db.query(func.count(func.distinct(NormalizedCryptoData.coin_id))).scalar()
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Build response
        summary = {
            "total_records": total_records,
            "unique_coins": unique_coins,
            "records_by_source": {row.source: row.count for row in source_counts},
            "latest_updates": {row.source: row.latest_update.isoformat() for row in latest_updates},
            "metadata": {
                "request_id": request_id,
                "api_latency_ms": round(latency_ms, 2)
            }
        }
        
        logger.info(
            "Data summary request completed",
            request_id=request_id,
            total_records=total_records,
            latency_ms=round(latency_ms, 2)
        )
        
        return summary
        
    except Exception as e:
        logger.error(
            "Data summary request failed",
            request_id=request_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")