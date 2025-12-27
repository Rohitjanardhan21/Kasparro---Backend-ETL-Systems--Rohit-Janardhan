"""Pydantic models for data validation and serialization."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class CoinPaprikaResponse(BaseModel):
    """CoinPaprika API response model."""
    id: str
    name: str
    symbol: str
    rank: Optional[int] = None
    price_usd: Optional[float] = Field(None, alias="price_usd")
    volume_24h_usd: Optional[float] = Field(None, alias="volume_24h_usd")
    market_cap_usd: Optional[float] = Field(None, alias="market_cap_usd")
    percent_change_1h: Optional[float] = Field(None, alias="percent_change_1h")
    percent_change_24h: Optional[float] = Field(None, alias="percent_change_24h")
    percent_change_7d: Optional[float] = Field(None, alias="percent_change_7d")
    
    @validator('price_usd', 'volume_24h_usd', 'market_cap_usd', pre=True)
    def parse_float_or_none(cls, v):
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class CoinGeckoResponse(BaseModel):
    """CoinGecko API response model."""
    id: str
    name: str
    symbol: str
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    market_cap_rank: Optional[int] = None
    total_volume: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    market_cap_change_24h: Optional[float] = None
    market_cap_change_percentage_24h: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    
    @validator('current_price', 'market_cap', 'total_volume', pre=True)
    def parse_float_or_none(cls, v):
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class CSVRowData(BaseModel):
    """Generic CSV row data model."""
    data: Dict[str, Any]
    
    @validator('data')
    def validate_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Data must be a dictionary")
        return v


class NormalizedCryptoResponse(BaseModel):
    """Normalized cryptocurrency data response."""
    id: UUID
    coin_id: str
    name: str
    symbol: str
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    rank: Optional[int] = None
    percent_change_24h: Optional[float] = None
    source: str
    processed_at: datetime
    
    class Config:
        from_attributes = True


class DataQueryParams(BaseModel):
    """Query parameters for data endpoint."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=100, ge=1, le=1000)
    source: Optional[str] = None
    coin_id: Optional[str] = None
    symbol: Optional[str] = None
    
    @validator('source')
    def validate_source(cls, v):
        if v and v not in ['coinpaprika', 'coingecko', 'csv']:
            raise ValueError("Source must be one of: coinpaprika, coingecko, csv")
        return v


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    database_connected: bool
    etl_last_run: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"


class StatsResponse(BaseModel):
    """ETL statistics response."""
    total_runs: int
    successful_runs: int
    failed_runs: int
    last_successful_run: Optional[Dict[str, Any]] = None
    last_failed_run: Optional[Dict[str, Any]] = None
    records_by_source: Dict[str, int]
    avg_duration_seconds: Optional[float] = None


class ETLRunResponse(BaseModel):
    """ETL run response."""
    id: UUID
    run_id: str
    source: str
    status: str
    records_processed: int
    records_inserted: int
    records_updated: int
    records_failed: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class DataResponse(BaseModel):
    """Paginated data response."""
    data: List[NormalizedCryptoResponse]
    pagination: Dict[str, Any]
    metadata: Dict[str, Any]