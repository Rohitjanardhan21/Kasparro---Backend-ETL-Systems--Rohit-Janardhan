"""CSV file data ingester."""

import pandas as pd
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime
import structlog

from .base_ingester import BaseIngester
from schemas.models import RawCSVData, NormalizedCryptoData
from core.database import get_db_session

logger = structlog.get_logger(__name__)


class CSVIngester(BaseIngester):
    """Ingester for CSV file data."""
    
    def __init__(self, csv_directory: str = "data"):
        super().__init__("csv")
        self.csv_directory = csv_directory
        self.supported_extensions = ['.csv', '.tsv']
    
    def _get_csv_files(self) -> List[str]:
        """Get list of CSV files to process."""
        if not os.path.exists(self.csv_directory):
            logger.warning(f"CSV directory does not exist: {self.csv_directory}")
            return []
        
        csv_files = []
        for filename in os.listdir(self.csv_directory):
            if any(filename.lower().endswith(ext) for ext in self.supported_extensions):
                csv_files.append(os.path.join(self.csv_directory, filename))
        
        return csv_files
    
    def _get_processed_files(self) -> set:
        """Get set of already processed files."""
        processed_files = set()
        
        try:
            with get_db_session() as db:
                # Get unique filenames from raw CSV data
                result = db.query(RawCSVData.filename).distinct().all()
                processed_files = {row[0] for row in result}
                
        except Exception as e:
            logger.warning("Failed to get processed files", error=str(e))
        
        return processed_files
    
    def extract_data(self) -> List[Dict[str, Any]]:
        """Extract data from CSV files."""
        csv_files = self._get_csv_files()
        processed_files = self._get_processed_files()
        
        raw_records = []
        
        for file_path in csv_files:
            filename = os.path.basename(file_path)
            
            # Skip if already processed (for incremental loading)
            if filename in processed_files:
                logger.info(f"Skipping already processed file: {filename}")
                continue
            
            try:
                logger.info(f"Processing CSV file: {filename}")
                
                # Read CSV file
                separator = '\t' if filename.lower().endswith('.tsv') else ','
                df = pd.read_csv(file_path, sep=separator)
                
                # Convert to records
                records = df.to_dict('records')
                
                # Store raw data
                with get_db_session() as db:
                    for row_number, record in enumerate(records, 1):
                        try:
                            # Clean the record (convert NaN to None)
                            cleaned_record = {}
                            for key, value in record.items():
                                if pd.isna(value):
                                    cleaned_record[key] = None
                                else:
                                    cleaned_record[key] = value
                            
                            raw_record = RawCSVData(
                                filename=filename,
                                row_number=row_number,
                                raw_data=cleaned_record
                            )
                            
                            db.add(raw_record)
                            db.flush()  # Generate the UUID
                            
                            raw_records.append({
                                "id": raw_record.id,  # Keep as UUID object
                                "filename": filename,
                                "row_number": row_number,
                                "data": cleaned_record
                            })
                            
                        except Exception as e:
                            logger.warning(
                                "Failed to process CSV row",
                                filename=filename,
                                row_number=row_number,
                                error=str(e)
                            )
                            continue
                    
                    db.commit()
                
                logger.info(
                    f"CSV file processed successfully",
                    filename=filename,
                    records_processed=len(records)
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to process CSV file",
                    filename=filename,
                    error=str(e)
                )
                continue
        
        # Update checkpoint
        if raw_records:
            self.checkpoint_service.set_checkpoint(
                "csv",
                "last_processed",
                datetime.utcnow().isoformat(),
                {"files_processed": len(set(r["filename"] for r in raw_records))}
            )
        
        logger.info(
            "CSV data extraction completed",
            records_extracted=len(raw_records)
        )
        
        return raw_records
    
    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw CSV data into normalized format."""
        transformed_records = []
        
        for record in raw_data:
            try:
                data = record["data"]
                
                # Try to map CSV columns to normalized schema
                # This is a flexible mapping that tries common column names
                normalized_record = {
                    "coin_id": self._get_field_value(data, ["id", "coin_id", "symbol", "ticker"]),
                    "name": self._get_field_value(data, ["name", "coin_name", "currency_name"]),
                    "symbol": self._get_field_value(data, ["symbol", "ticker", "code"]),
                    "price_usd": self._get_numeric_field(data, ["price", "price_usd", "current_price", "value"]),
                    "market_cap_usd": self._get_numeric_field(data, ["market_cap", "market_cap_usd", "mcap"]),
                    "volume_24h_usd": self._get_numeric_field(data, ["volume", "volume_24h", "daily_volume"]),
                    "rank": self._get_numeric_field(data, ["rank", "market_cap_rank", "position"], int),
                    "percent_change_24h": self._get_numeric_field(data, ["change_24h", "percent_change_24h", "daily_change"]),
                    "source": "csv",
                    "source_id": record["id"]  # This is now a UUID object
                }
                
                # Only include records with minimum required fields
                if normalized_record["coin_id"] and normalized_record["name"]:
                    # Ensure symbol is uppercase
                    if normalized_record["symbol"]:
                        normalized_record["symbol"] = str(normalized_record["symbol"]).upper()
                    
                    transformed_records.append(normalized_record)
                else:
                    logger.warning(
                        "Skipping CSV record with missing required fields",
                        filename=record["filename"],
                        row_number=record["row_number"]
                    )
                
            except Exception as e:
                logger.warning(
                    "Failed to transform CSV record",
                    filename=record.get("filename", "unknown"),
                    row_number=record.get("row_number", "unknown"),
                    error=str(e)
                )
                continue
        
        logger.info(
            "CSV data transformation completed",
            records_transformed=len(transformed_records)
        )
        
        return transformed_records
    
    def _get_field_value(self, data: Dict[str, Any], possible_keys: List[str]) -> Any:
        """Get field value from data using possible key names."""
        for key in possible_keys:
            # Try exact match
            if key in data and data[key] is not None:
                return data[key]
            
            # Try case-insensitive match
            for data_key in data.keys():
                if data_key.lower() == key.lower() and data[data_key] is not None:
                    return data[data_key]
        
        return None
    
    def _get_numeric_field(self, data: Dict[str, Any], possible_keys: List[str], convert_type=float) -> Any:
        """Get numeric field value from data."""
        value = self._get_field_value(data, possible_keys)
        
        if value is None:
            return None
        
        try:
            # Handle string representations
            if isinstance(value, str):
                # Remove common formatting
                value = value.replace(',', '').replace('$', '').replace('%', '')
                if value == '' or value.lower() in ['n/a', 'null', 'none']:
                    return None
            
            return convert_type(value)
        except (ValueError, TypeError):
            return None
    
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
                            "Failed to load CSV record",
                            coin_id=record.get("coin_id", "unknown"),
                            error=str(e)
                        )
                        continue
                
                db.commit()
                
        except Exception as e:
            logger.error("Failed to load CSV data", error=str(e))
            raise
        
        logger.info(
            "CSV data loading completed",
            records_loaded=loaded_count
        )
        
        return loaded_count