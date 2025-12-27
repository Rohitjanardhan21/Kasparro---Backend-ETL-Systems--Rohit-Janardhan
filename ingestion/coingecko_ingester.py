"""CoinGecko API data ingester."""

import requests
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from .base_ingester import BaseIngester
from services.rate_limiter import RateLimitConfig, RetryableError, with_retry_and_rate_limit
from schemas.models import RawCoinGeckoData, NormalizedCryptoData
from schemas.pydantic_models import CoinGeckoResponse
from core.database import get_db_session
from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CoinGeckoIngester(BaseIngester):
    """Ingester for CoinGecko API data."""
    
    def __init__(self):
        rate_limit_config = RateLimitConfig(
            requests_per_period=settings.etl_rate_limit_requests,
            period_seconds=settings.etl_rate_limit_period,
            max_retries=settings.etl_retry_attempts,
            base_delay=settings.etl_retry_delay
        )
        super().__init__("coingecko", rate_limit_config)
        self.api_key = settings.coingecko_api_key
        self.base_url = "https://api.coingecko.com/api/v3"
    
    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with rate limiting and retry logic."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Accept": "application/json"
        }
        
        # Add API key to headers if available (CoinGecko Pro)
        if self.api_key and self.api_key != "your_coingecko_api_key_here":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed("coingecko")
            
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
        """Extract data from CoinGecko API."""
        try:
            # Get last checkpoint
            last_page = self.checkpoint_service.get_checkpoint("coingecko", "page")
            start_page = int(last_page) + 1 if last_page else 1
            
            # Get coins market data
            logger.info(f"Fetching CoinGecko market data starting from page {start_page}")
            
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": start_page,
                "sparkline": False,
                "price_change_percentage": "24h"
            }
            
            market_data = self._make_api_request("coins/markets", params)
            
            # Store raw data
            raw_records = []
            
            with get_db_session() as db:
                for coin in market_data:
                    try:
                        # Validate data structure
                        validated_coin = CoinGeckoResponse(**coin)
                        
                        # Create raw record
                        raw_record = RawCoinGeckoData(
                            coin_id=validated_coin.id,
                            name=validated_coin.name,
                            symbol=validated_coin.symbol,
                            current_price=validated_coin.current_price,
                            market_cap=validated_coin.market_cap,
                            market_cap_rank=validated_coin.market_cap_rank,
                            total_volume=validated_coin.total_volume,
                            high_24h=validated_coin.high_24h,
                            low_24h=validated_coin.low_24h,
                            price_change_24h=validated_coin.price_change_24h,
                            price_change_percentage_24h=validated_coin.price_change_percentage_24h,
                            market_cap_change_24h=validated_coin.market_cap_change_24h,
                            market_cap_change_percentage_24h=validated_coin.market_cap_change_percentage_24h,
                            circulating_supply=validated_coin.circulating_supply,
                            total_supply=validated_coin.total_supply,
                            max_supply=validated_coin.max_supply,
                            raw_data=coin
                        )
                        
                        db.add(raw_record)
                        db.flush()  # Generate the UUID
                        
                        raw_records.append({
                            "id": raw_record.id,  # Keep as UUID object
                            "data": coin,
                            "validated": validated_coin.dict()
                        })
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to validate coin data",
                            coin_id=coin.get("id", "unknown"),
                            error=str(e)
                        )
                        continue
                
                db.commit()
            
            # Update checkpoint
            self.checkpoint_service.set_checkpoint(
                "coingecko",
                "page",
                str(start_page),
                {"records_processed": len(raw_records)}
            )
            
            logger.info(
                "CoinGecko data extraction completed",
                records_extracted=len(raw_records),
                page=start_page
            )
            
            return raw_records
            
        except Exception as e:
            logger.error("CoinGecko data extraction failed", error=str(e))
            raise
    
    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw CoinGecko data into normalized format."""
        transformed_records = []
        
        for record in raw_data:
            try:
                validated_data = record["validated"]
                
                normalized_record = {
                    "coin_id": validated_data["id"],
                    "name": validated_data["name"],
                    "symbol": validated_data["symbol"].upper(),
                    "price_usd": validated_data.get("current_price"),
                    "market_cap_usd": validated_data.get("market_cap"),
                    "volume_24h_usd": validated_data.get("total_volume"),
                    "rank": validated_data.get("market_cap_rank"),
                    "percent_change_24h": validated_data.get("price_change_percentage_24h"),
                    "source": "coingecko",
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
            "CoinGecko data transformation completed",
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
            logger.error("Failed to load CoinGecko data", error=str(e))
            raise
        
        logger.info(
            "CoinGecko data loading completed",
            records_loaded=loaded_count
        )
        
        return loaded_count