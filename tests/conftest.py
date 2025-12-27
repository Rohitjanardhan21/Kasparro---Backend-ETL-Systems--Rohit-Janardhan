"""Test configuration and fixtures."""

import pytest
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from core.database import Base, get_db
from core.config import Settings
from api.main import app


@pytest.fixture(scope="session")
def test_settings():
    """Test settings with PostgreSQL test database."""
    # Use the same PostgreSQL database as the running container
    return Settings(
        database_url="postgresql://postgres:postgres@db:5432/postgres",
        coinpaprika_api_key="test_key",
        coingecko_api_key="test_key",
        log_level="DEBUG",
        environment="test"
    )


@pytest.fixture(scope="session")
def test_engine(test_settings):
    """Create test database engine."""
    engine = create_engine(test_settings.database_url)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Create a new session for each test
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        
        # Clean up tables after each test
        from schemas.models import NormalizedCryptoData, RawCSVData, RawCoinPaprikaData, RawCoinGeckoData, ETLRun, ETLCheckpoint
        
        # Delete in reverse dependency order
        for model in [NormalizedCryptoData, RawCSVData, RawCoinPaprikaData, RawCoinGeckoData, ETLRun, ETLCheckpoint]:
            try:
                session.query(model).delete()
                session.commit()
            except Exception:
                session.rollback()


@pytest.fixture(scope="function")
def test_client(test_db):
    """Create test client with database dependency override."""
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_crypto_data():
    """Sample cryptocurrency data for testing."""
    return [
        {
            "id": "bitcoin",
            "name": "Bitcoin",
            "symbol": "BTC",
            "rank": 1,
            "price_usd": 50000.0,
            "volume_24h_usd": 1000000000.0,
            "market_cap_usd": 900000000000.0,
            "percent_change_24h": 2.5
        },
        {
            "id": "ethereum",
            "name": "Ethereum",
            "symbol": "ETH",
            "rank": 2,
            "price_usd": 3000.0,
            "volume_24h_usd": 500000000.0,
            "market_cap_usd": 350000000000.0,
            "percent_change_24h": -1.2
        }
    ]


@pytest.fixture(scope="function")
def temp_csv_file():
    """Create a temporary CSV file for testing."""
    csv_content = """id,name,symbol,price,market_cap,volume
bitcoin,Bitcoin,BTC,50000,900000000000,1000000000
ethereum,Ethereum,ETH,3000,350000000000,500000000
cardano,Cardano,ADA,1.5,50000000000,100000000"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)