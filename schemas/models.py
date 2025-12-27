"""Database models for the ETL system."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from core.database import Base


class RawCoinPaprikaData(Base):
    """Raw data from CoinPaprika API."""
    __tablename__ = "raw_coinpaprika_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coin_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    rank = Column(Integer)
    price_usd = Column(Float)
    volume_24h_usd = Column(Float)
    market_cap_usd = Column(Float)
    percent_change_1h = Column(Float)
    percent_change_24h = Column(Float)
    percent_change_7d = Column(Float)
    raw_data = Column(JSONB)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_coinpaprika_coin_id', 'coin_id'),
        Index('idx_coinpaprika_ingested_at', 'ingested_at'),
    )


class RawCoinGeckoData(Base):
    """Raw data from CoinGecko API."""
    __tablename__ = "raw_coingecko_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coin_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    current_price = Column(Float)
    market_cap = Column(Float)
    market_cap_rank = Column(Integer)
    total_volume = Column(Float)
    high_24h = Column(Float)
    low_24h = Column(Float)
    price_change_24h = Column(Float)
    price_change_percentage_24h = Column(Float)
    market_cap_change_24h = Column(Float)
    market_cap_change_percentage_24h = Column(Float)
    circulating_supply = Column(Float)
    total_supply = Column(Float)
    max_supply = Column(Float)
    raw_data = Column(JSONB)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_coingecko_coin_id', 'coin_id'),
        Index('idx_coingecko_ingested_at', 'ingested_at'),
    )


class RawCSVData(Base):
    """Raw data from CSV files."""
    __tablename__ = "raw_csv_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSONB, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_csv_filename', 'filename'),
        Index('idx_csv_ingested_at', 'ingested_at'),
    )


class NormalizedCryptoData(Base):
    """Normalized cryptocurrency data from all sources."""
    __tablename__ = "normalized_crypto_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coin_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    price_usd = Column(Float)
    market_cap_usd = Column(Float)
    volume_24h_usd = Column(Float)
    rank = Column(Integer)
    percent_change_24h = Column(Float)
    source = Column(String, nullable=False)  # 'coinpaprika', 'coingecko', 'csv'
    source_id = Column(UUID(as_uuid=True), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_normalized_coin_id', 'coin_id'),
        Index('idx_normalized_source', 'source'),
        Index('idx_normalized_processed_at', 'processed_at'),
    )


class ETLCheckpoint(Base):
    """ETL checkpoint tracking for incremental processing."""
    __tablename__ = "etl_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)  # 'coinpaprika', 'coingecko', 'csv'
    checkpoint_type = Column(String, nullable=False)  # 'timestamp', 'offset', 'page'
    checkpoint_value = Column(String, nullable=False)
    metadata_json = Column('metadata', JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_checkpoint_source', 'source'),
        Index('idx_checkpoint_type', 'checkpoint_type'),
    )


class ETLRun(Base):
    """ETL run metadata and statistics."""
    __tablename__ = "etl_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(String, nullable=False, unique=True)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False)  # 'running', 'completed', 'failed'
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    error_message = Column(Text)
    metadata_json = Column('metadata', JSONB)
    
    __table_args__ = (
        Index('idx_etl_run_source', 'source'),
        Index('idx_etl_run_status', 'status'),
        Index('idx_etl_run_start_time', 'start_time'),
    )