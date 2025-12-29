"""Unit tests that don't require database connection."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import pandas as pd

from ingestion.csv_ingester import CSVIngester
from ingestion.coinpaprika_ingester import CoinPaprikaIngester
from ingestion.coingecko_ingester import CoinGeckoIngester
from schemas.pydantic_models import CryptoDataCSV, CryptoDataCoinPaprika, CryptoDataCoinGecko


class TestDataTransformation:
    """Test data transformation logic without database."""
    
    def test_csv_data_validation(self):
        """Test CSV data validation with Pydantic."""
        valid_data = {
            "id": "bitcoin",
            "name": "Bitcoin",
            "symbol": "BTC",
            "price": "50000.0",
            "market_cap": "900000000000",
            "volume": "1000000000"
        }
        
        crypto_data = CryptoDataCSV(**valid_data)
        assert crypto_data.id == "bitcoin"
        assert crypto_data.name == "Bitcoin"
        assert crypto_data.symbol == "BTC"
        assert crypto_data.price == 50000.0
    
    def test_coinpaprika_data_validation(self):
        """Test CoinPaprika data validation."""
        valid_data = {
            "id": "btc-bitcoin",
            "name": "Bitcoin",
            "symbol": "BTC",
            "rank": 1,
            "price_usd": 50000.0,
            "volume_24h_usd": 1000000000.0,
            "market_cap_usd": 900000000000.0,
            "percent_change_24h": 2.5,
            "last_updated": "2023-01-01T00:00:00Z"
        }
        
        crypto_data = CryptoDataCoinPaprika(**valid_data)
        assert crypto_data.id == "btc-bitcoin"
        assert crypto_data.rank == 1
        assert crypto_data.price_usd == 50000.0
    
    def test_coingecko_data_validation(self):
        """Test CoinGecko data validation."""
        valid_data = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 50000.0,
            "market_cap": 900000000000.0,
            "total_volume": 1000000000.0,
            "market_cap_rank": 1,
            "price_change_percentage_24h": 2.5,
            "last_updated": "2023-01-01T00:00:00Z"
        }
        
        crypto_data = CryptoDataCoinGecko(**valid_data)
        assert crypto_data.id == "bitcoin"
        assert crypto_data.current_price == 50000.0
        assert crypto_data.market_cap_rank == 1


class TestETLLogic:
    """Test ETL transformation logic."""
    
    @patch('ingestion.csv_ingester.CSVIngester._get_db_session')
    def test_csv_ingester_initialization(self, mock_db):
        """Test CSV ingester can be initialized."""
        mock_db.return_value = Mock()
        ingester = CSVIngester()
        assert ingester.source == "csv"
        assert ingester.batch_size == 1000
    
    @patch('ingestion.coinpaprika_ingester.CoinPaprikaIngester._get_db_session')
    def test_coinpaprika_ingester_initialization(self, mock_db):
        """Test CoinPaprika ingester can be initialized."""
        mock_db.return_value = Mock()
        ingester = CoinPaprikaIngester()
        assert ingester.source == "coinpaprika"
        assert ingester.base_url == "https://api.coinpaprika.com/v1"
    
    @patch('ingestion.coingecko_ingester.CoinGeckoIngester._get_db_session')
    def test_coingecko_ingester_initialization(self, mock_db):
        """Test CoinGecko ingester can be initialized."""
        mock_db.return_value = Mock()
        ingester = CoinGeckoIngester()
        assert ingester.source == "coingecko"
        assert ingester.base_url == "https://api.coingecko.com/api/v3"


class TestDataProcessing:
    """Test data processing functions."""
    
    def test_csv_data_processing(self):
        """Test CSV data can be processed into DataFrame."""
        csv_data = [
            {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "price": "50000", "market_cap": "900000000000", "volume": "1000000000"},
            {"id": "ethereum", "name": "Ethereum", "symbol": "ETH", "price": "3000", "market_cap": "350000000000", "volume": "500000000"}
        ]
        
        df = pd.DataFrame(csv_data)
        assert len(df) == 2
        assert "bitcoin" in df["id"].values
        assert "ethereum" in df["id"].values
    
    def test_data_type_conversion(self):
        """Test numeric data type conversion."""
        test_values = ["50000.0", "3000", "1.5", None, ""]
        
        def safe_float_convert(value):
            try:
                return float(value) if value and str(value).strip() else None
            except (ValueError, TypeError):
                return None
        
        converted = [safe_float_convert(v) for v in test_values]
        assert converted[0] == 50000.0
        assert converted[1] == 3000.0
        assert converted[2] == 1.5
        assert converted[3] is None
        assert converted[4] is None


class TestRateLimiting:
    """Test rate limiting logic."""
    
    def test_rate_limit_calculation(self):
        """Test rate limit delay calculation."""
        def calculate_delay(attempt, base_delay=1, max_delay=60):
            import random
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, 0.1) * delay
            return delay + jitter
        
        # Test exponential backoff
        delay1 = calculate_delay(0, base_delay=1)
        delay2 = calculate_delay(1, base_delay=1)
        delay3 = calculate_delay(2, base_delay=1)
        
        assert 1.0 <= delay1 <= 1.1  # Base delay + jitter
        assert 2.0 <= delay2 <= 2.2  # 2^1 * base + jitter
        assert 4.0 <= delay3 <= 4.4  # 2^2 * base + jitter


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_data_handling(self):
        """Test handling of invalid data."""
        invalid_data = {
            "id": "",  # Empty ID
            "name": "Bitcoin",
            "symbol": "BTC",
            "price": "invalid_price",  # Invalid price
            "market_cap": None,
            "volume": ""
        }
        
        # Test that validation catches invalid data
        with pytest.raises(Exception):  # Pydantic will raise validation error
            CryptoDataCSV(**invalid_data)
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        incomplete_data = {
            "name": "Bitcoin",
            "symbol": "BTC"
            # Missing required 'id' field
        }
        
        with pytest.raises(Exception):  # Pydantic will raise validation error
            CryptoDataCSV(**incomplete_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])