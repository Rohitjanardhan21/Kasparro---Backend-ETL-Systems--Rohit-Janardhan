"""Tests for ETL functionality."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import os
import tempfile

from ingestion.base_ingester import BaseIngester
from ingestion.csv_ingester import CSVIngester
from services.checkpoint_service import CheckpointService
from services.rate_limiter import RateLimiter, RateLimitConfig
from schemas.models import ETLRun, ETLCheckpoint, NormalizedCryptoData


class TestBaseIngester:
    """Test the base ingester functionality."""
    
    def test_start_run(self, test_db):
        """Test starting an ETL run."""
        
        class TestIngester(BaseIngester):
            def extract_data(self):
                return []
            
            def transform_data(self, raw_data):
                return []
            
            def load_data(self, transformed_data):
                return 0
        
        ingester = TestIngester("test_source")
        
        # Mock the database session
        with patch('ingestion.base_ingester.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            run_id = ingester.start_run()
            
            assert run_id is not None
            assert run_id.startswith("test_source_")
            assert ingester.current_run_id == run_id
    
    def test_complete_run(self, test_db):
        """Test completing an ETL run."""
        
        class TestIngester(BaseIngester):
            def extract_data(self):
                return []
            
            def transform_data(self, raw_data):
                return []
            
            def load_data(self, transformed_data):
                return 0
        
        ingester = TestIngester("test_source")
        
        with patch('ingestion.base_ingester.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Start and complete a run
            run_id = ingester.start_run()
            ingester.complete_run(success=True)
            
            # Verify run is completed
            run = test_db.query(ETLRun).filter(ETLRun.run_id == run_id).first()
            assert run is not None
            assert run.status == "completed"
            assert run.end_time is not None


class TestCSVIngester:
    """Test CSV ingestion functionality."""
    
    def test_csv_extraction(self, test_db, temp_csv_file):
        """Test CSV data extraction."""
        
        # Create CSV ingester with temp directory
        temp_dir = os.path.dirname(temp_csv_file)
        ingester = CSVIngester(csv_directory=temp_dir)
        
        with patch('ingestion.csv_ingester.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Extract data
            raw_data = ingester.extract_data()
            
            assert len(raw_data) == 3  # 3 rows in test CSV
            assert raw_data[0]["data"]["name"] == "Bitcoin"
            assert raw_data[1]["data"]["symbol"] == "ETH"
    
    def test_csv_transformation(self, test_db):
        """Test CSV data transformation."""
        
        ingester = CSVIngester()
        
        # Sample raw data
        raw_data = [
            {
                "id": "test-id-1",
                "filename": "test.csv",
                "row_number": 1,
                "data": {
                    "id": "bitcoin",
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "price": "50000",
                    "market_cap": "900000000000"
                }
            }
        ]
        
        # Transform data
        transformed_data = ingester.transform_data(raw_data)
        
        assert len(transformed_data) == 1
        assert transformed_data[0]["coin_id"] == "bitcoin"
        assert transformed_data[0]["name"] == "Bitcoin"
        assert transformed_data[0]["symbol"] == "BTC"
        assert transformed_data[0]["price_usd"] == 50000.0
        assert transformed_data[0]["source"] == "csv"
    
    def test_csv_loading(self, test_db):
        """Test CSV data loading."""
        
        ingester = CSVIngester()
        
        # Sample transformed data
        transformed_data = [
            {
                "coin_id": "bitcoin",
                "name": "Bitcoin",
                "symbol": "BTC",
                "price_usd": 50000.0,
                "market_cap_usd": 900000000000.0,
                "volume_24h_usd": 1000000000.0,
                "rank": 1,
                "percent_change_24h": 2.5,
                "source": "csv",
                "source_id": "test-id-1"
            }
        ]
        
        with patch('ingestion.csv_ingester.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Load data
            loaded_count = ingester.load_data(transformed_data)
            
            assert loaded_count == 1
            
            # Verify data was loaded
            record = test_db.query(NormalizedCryptoData).first()
            assert record is not None
            assert record.coin_id == "bitcoin"
            assert record.name == "Bitcoin"


class TestCheckpointService:
    """Test checkpoint service functionality."""
    
    def test_set_and_get_checkpoint(self, test_db):
        """Test setting and getting checkpoints."""
        
        service = CheckpointService()
        
        with patch('services.checkpoint_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Set checkpoint
            success = service.set_checkpoint("test_source", "timestamp", "2023-01-01T00:00:00")
            assert success is True
            
            # Get checkpoint
            value = service.get_checkpoint("test_source", "timestamp")
            assert value == "2023-01-01T00:00:00"
    
    def test_checkpoint_update(self, test_db):
        """Test updating existing checkpoint."""
        
        service = CheckpointService()
        
        with patch('services.checkpoint_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Set initial checkpoint
            service.set_checkpoint("test_source", "timestamp", "2023-01-01T00:00:00")
            
            # Update checkpoint
            service.set_checkpoint("test_source", "timestamp", "2023-01-02T00:00:00")
            
            # Verify update
            value = service.get_checkpoint("test_source", "timestamp")
            assert value == "2023-01-02T00:00:00"
            
            # Verify only one checkpoint exists
            checkpoints = test_db.query(ETLCheckpoint).filter(
                ETLCheckpoint.source == "test_source"
            ).all()
            assert len(checkpoints) == 1


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limit_allows_requests(self):
        """Test that rate limiter allows requests under the limit."""
        
        config = RateLimitConfig(requests_per_period=5, period_seconds=60)
        limiter = RateLimiter(config)
        
        # Should allow first 5 requests
        for i in range(5):
            assert limiter.is_allowed("test_key") is True
        
        # Should deny 6th request
        assert limiter.is_allowed("test_key") is False
    
    def test_rate_limit_different_keys(self):
        """Test that rate limiter tracks different keys separately."""
        
        config = RateLimitConfig(requests_per_period=2, period_seconds=60)
        limiter = RateLimiter(config)
        
        # Use up limit for key1
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is True
        assert limiter.is_allowed("key1") is False
        
        # key2 should still be allowed
        assert limiter.is_allowed("key2") is True
        assert limiter.is_allowed("key2") is True
        assert limiter.is_allowed("key2") is False
    
    def test_retry_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        
        config = RateLimitConfig(
            requests_per_period=1,
            period_seconds=60,
            base_delay=1.0,
            max_delay=10.0
        )
        limiter = RateLimiter(config)
        
        # Test exponential backoff
        assert limiter.get_retry_delay(0) == 1.0
        assert limiter.get_retry_delay(1) == 2.0
        assert limiter.get_retry_delay(2) == 4.0
        assert limiter.get_retry_delay(3) == 8.0
        assert limiter.get_retry_delay(4) == 10.0  # Capped at max_delay


class TestETLFailureScenarios:
    """Test ETL failure scenarios and recovery."""
    
    def test_extraction_failure(self, test_db):
        """Test handling of extraction failures."""
        
        class FailingIngester(BaseIngester):
            def extract_data(self):
                raise Exception("Extraction failed")
            
            def transform_data(self, raw_data):
                return []
            
            def load_data(self, transformed_data):
                return 0
        
        ingester = FailingIngester("test_source")
        
        with patch('ingestion.base_ingester.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Run should fail gracefully
            result = ingester.run()
            
            assert result["status"] == "failed"
            assert "Extraction failed" in result["error"]
    
    def test_transformation_failure(self, test_db):
        """Test handling of transformation failures."""
        
        class FailingTransformIngester(BaseIngester):
            def extract_data(self):
                return [{"test": "data"}]
            
            def transform_data(self, raw_data):
                raise Exception("Transformation failed")
            
            def load_data(self, transformed_data):
                return 0
        
        ingester = FailingTransformIngester("test_source")
        
        with patch('ingestion.base_ingester.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Run should fail gracefully
            result = ingester.run()
            
            assert result["status"] == "failed"
            assert "Transformation failed" in result["error"]
    
    def test_loading_failure(self, test_db):
        """Test handling of loading failures."""
        
        class FailingLoadIngester(BaseIngester):
            def extract_data(self):
                return [{"test": "data"}]
            
            def transform_data(self, raw_data):
                return [{"transformed": "data"}]
            
            def load_data(self, transformed_data):
                raise Exception("Loading failed")
        
        ingester = FailingLoadIngester("test_source")
        
        with patch('ingestion.base_ingester.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_db
            
            # Run should fail gracefully
            result = ingester.run()
            
            assert result["status"] == "failed"
            assert "Loading failed" in result["error"]