"""CoinPaprika API data ingester."""

import requests
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from .base_ingester import BaseIngester
from services.rate_limiter import RateLimitConfig, RetryableError, with_retry_and_rate_limit
from schemas.models import RawCoinPaprikaData, NormalizedCryptoData
from schemas.pydantic_models import CoinPaprikaResponse
from core.database import get_db_session
from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CoinPaprikaIngester(BaseIngester):
    """Ingester for CoinPaprika API data."""
    
    def __init__(self):
        rate_limit_config = RateLimitConfig(
            requests_per_period=settings.etl_rate_limit_requests,
            period_seconds=settings.etl_rate_limit_period,
            max_retries=settings.etl_retry_attempts,
            base_delay=settings.etl_retry_delay
        )
        super().__init__("coinpaprika", rate_limit_config)
        self.api_key = settings.coinpaprika_api_key
        self.base_url = "https://api.coinpaprika.com/v1"
    
    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with rate limiting and retry logic."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Accept": "application/json"
        }
        
        # Add API key to headers if available (CoinPaprika Pro)
        if self.api_key and self.api_key != "your_coinpaprika_api_key_here":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed("coinpaprika")
            
            response = requests.get(url, headers=headers, params=params or {}, timeout=30)
            
            if response.status_code == 429:  # Rate limited
                raise RetryableError("Rate limit exceeded")
            elif response.status_code >= 500:  # Server error
                raise RetryableError(f"Server error: {response.status_code}")
            elif response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise RetryableError(f"Request failed: {str(e)}")
    
    def extract_data(self) -> List[Dict[str, Any]]:
        """Extract data from CoinPaprika API."""
        try:
            # Get last checkpoint
            last_timestamp = self.checkpoint_service.get_checkpoint("coinpaprika", "timestamp")
            
            # Get tickers data from CoinPaprika
            logger.info("Fetching CoinPaprika tickers data")
            tickers_data = self._make_api_request("tickers")
            
            # Filter for new data if we have a checkpoint
            if last_timestamp:
                logger.info(f"Processing data since checkpoint: {last_timestamp}")
            
            # Store raw data
            raw_records = []
            current_timestamp = datetime.utcnow().isoformat()
            
            with get_db_session() as db:
                for ticker in tickers_data[:100]:  # Limit for demo to avoid rate limits
                    try:
                        # Map CoinPaprika response to our expected format
                        mapped_ticker = {
                            "id": ticker.get("id"),
                            "name": ticker.get("name"),
                            "symbol": ticker.get("symbol"),
                            "rank": ticker.get("rank"),
                            "price_usd": ticker.get("quotes", {}).get("USD", {}).get("price") if ticker.get("quotes") else None,
                            "volume_24h_usd": ticker.get("quotes", {}).get("USD", {}).get("volume_24h") if ticker.get("quotes") else None,
                            "market_cap_usd": ticker.get("quotes", {}).get("USD", {}).get("market_cap") if ticker.get("quotes") else None,
                            "percent_change_1h": ticker.get("quotes", {}).get("USD", {}).get("percent_change_1h") if ticker.get("quotes") else None,
                            "percent_change_24h": ticker.get("quotes", {}).get("USD", {}).get("percent_change_24h") if ticker.get("quotes") else None,
                            "percent_change_7d": ticker.get("quotes", {}).get("USD", {}).get("percent_change_7d") if ticker.get("quotes") else None,
                        }
                        
                        # Validate data structure
                        validated_ticker = CoinPaprikaResponse(**mapped_ticker)
                        
                        # Create raw record
                        raw_record = RawCoinPaprikaData(
                            coin_id=validated_ticker.id,
                            name=validated_ticker.name,
                            symbol=validated_ticker.symbol,
                            rank=validated_ticker.rank,
                            price_usd=validated_ticker.price_usd,
                            volume_24h_usd=validated_ticker.volume_24h_usd,
                            market_cap_usd=validated_ticker.market_cap_usd,
                            percent_change_1h=validated_ticker.percent_change_1h,
                            percent_change_24h=validated_ticker.percent_change_24h,
                            percent_change_7d=validated_ticker.percent_change_7d,
                            raw_data=ticker
                        )
                        
                        db.add(raw_record)
                        db.flush()  # Generate the UUID
                        
                        raw_records.append({
                            "id": raw_record.id,  # Keep as UUID object
                            "data": ticker,
                            "validated": validated_ticker.dict()
                        })
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to validate ticker data",
                            ticker_id=ticker.get("id", "unknown"),
                            error=str(e)
                        )
                        continue
                
                db.commit()
            
            # Update checkpoint
            self.checkpoint_service.set_checkpoint(
                "coinpaprika",
                "timestamp",
                current_timestamp,
                {"records_processed": len(raw_records)}
            )
            
            logger.info(
                "CoinPaprika data extraction completed",
                records_extracted=len(raw_records)
            )
            
            return raw_records
            
        except Exception as e:
            logger.error("CoinPaprika data extraction failed", error=str(e))
            raise
    
    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw CoinPaprika data into normalized format."""
        transformed_records = []
        
        for record in raw_data:
            try:
                validated_data = record["validated"]
                
                normalized_record = {
                    "coin_id": validated_data["id"],
                    "name": validated_data["name"],
                    "symbol": validated_data["symbol"].upper(),
                    "price_usd": validated_data.get("price_usd"),
                    "market_cap_usd": validated_data.get("market_cap_usd"),
                    "volume_24h_usd": validated_data.get("volume_24h_usd"),
                    "rank": validated_data.get("rank"),
                    "percent_change_24h": validated_data.get("percent_change_24h"),
                    "source": "coinpaprika",
                    "source_id": record["id"]  # This is now a UUID object
                }
                
                transformed_records.append(normalized_record)
                
            except Exception as e:
                logger.warning(
                    "Failed to transform record",
                    record_id=record.get("id", "unknown"),
                    error=str(e)
                )
                continue
        
        logger.info(
            "CoinPaprika data transformation completed",
            records_transformed=len(transformed_records)
        )
        
        return transformed_records
    
    def load_data(self, transformed_data: List[Dict[str, Any]]) -> int:
        """Load transformed data into normalized table."""
        loaded_count = 0
        
        try:
            with get_db_session() as db:
                for record in transformed_data:
                    try:
                        normalized_record = NormalizedCryptoData(**record)
                        db.add(normalized_record)
                        loaded_count += 1
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to load record",
                            coin_id=record.get("coin_id", "unknown"),
                            error=str(e)
                        )
                        continue
                
                db.commit()
                
        except Exception as e:
            logger.error("Failed to load CoinPaprika data", error=str(e))
            raise
        
        logger.info(
            "CoinPaprika data loading completed",
            records_loaded=loaded_count
        )
        
        return loaded_count