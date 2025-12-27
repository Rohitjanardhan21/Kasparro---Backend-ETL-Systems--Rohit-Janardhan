"""Main ETL orchestrator."""

import asyncio
from typing import List, Dict, Any
import structlog

from .coinpaprika_ingester import CoinPaprikaIngester
from .coingecko_ingester import CoinGeckoIngester
from .csv_ingester import CSVIngester
from core.logging import setup_logging
from core.database import init_db

logger = structlog.get_logger(__name__)


class ETLOrchestrator:
    """Orchestrates ETL processes for all data sources."""
    
    def __init__(self):
        self.ingesters = {
            "coinpaprika": CoinPaprikaIngester(),
            "coingecko": CoinGeckoIngester(),
            "csv": CSVIngester()
        }
    
    def run_single_source(self, source: str) -> Dict[str, Any]:
        """Run ETL for a single data source."""
        if source not in self.ingesters:
            raise ValueError(f"Unknown source: {source}")
        
        logger.info(f"Starting ETL for source: {source}")
        
        try:
            ingester = self.ingesters[source]
            result = ingester.run()
            
            logger.info(
                f"ETL completed for source: {source}",
                result=result
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"ETL failed for source: {source}",
                error=str(e)
            )
            return {
                "source": source,
                "status": "failed",
                "error": str(e)
            }
    
    def run_all_sources(self) -> Dict[str, Dict[str, Any]]:
        """Run ETL for all data sources."""
        logger.info("Starting ETL for all sources")
        
        results = {}
        
        for source in self.ingesters.keys():
            try:
                results[source] = self.run_single_source(source)
            except Exception as e:
                logger.error(
                    f"Failed to run ETL for source: {source}",
                    error=str(e)
                )
                results[source] = {
                    "source": source,
                    "status": "failed",
                    "error": str(e)
                }
        
        # Summary
        successful = sum(1 for r in results.values() if r.get("status") == "completed")
        total = len(results)
        
        logger.info(
            "ETL completed for all sources",
            successful=successful,
            total=total,
            results=results
        )
        
        return results
    
    async def run_all_sources_async(self) -> Dict[str, Dict[str, Any]]:
        """Run ETL for all sources asynchronously."""
        logger.info("Starting async ETL for all sources")
        
        # Create tasks for each source
        tasks = []
        for source in self.ingesters.keys():
            task = asyncio.create_task(
                asyncio.to_thread(self.run_single_source, source)
            )
            tasks.append((source, task))
        
        # Wait for all tasks to complete
        results = {}
        for source, task in tasks:
            try:
                results[source] = await task
            except Exception as e:
                logger.error(
                    f"Async ETL failed for source: {source}",
                    error=str(e)
                )
                results[source] = {
                    "source": source,
                    "status": "failed",
                    "error": str(e)
                }
        
        return results


def main():
    """Main entry point for ETL process."""
    # Setup logging
    setup_logging()
    
    # Initialize database
    logger.info("Initializing database")
    init_db()
    
    # Create orchestrator
    orchestrator = ETLOrchestrator()
    
    # Run ETL
    try:
        results = orchestrator.run_all_sources()
        
        # Print summary
        print("\n" + "="*50)
        print("ETL EXECUTION SUMMARY")
        print("="*50)
        
        for source, result in results.items():
            status = result.get("status", "unknown")
            records = result.get("records_processed", 0)
            
            print(f"{source.upper()}: {status} ({records} records)")
            
            if status == "failed":
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print("="*50)
        
    except Exception as e:
        logger.error("ETL orchestration failed", error=str(e))
        raise


if __name__ == "__main__":
    main()