"""Tests for API endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from schemas.models import NormalizedCryptoData, ETLRun


class TestDataEndpoint:
    """Test the /data endpoint."""
    
    def test_get_data_empty(self, test_client):
        """Test data endpoint with no data."""
        response = test_client.get("/api/v1/data")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "pagination" in data
        assert "metadata" in data
        assert len(data["data"]) == 0
        assert data["pagination"]["total_records"] == 0
    
    def test_get_data_with_records(self, test_client, test_db):
        """Test data endpoint with sample records."""
        
        # Add sample data
        sample_record = NormalizedCryptoData(
            coin_id="bitcoin",
            name="Bitcoin",
            symbol="BTC",
            price_usd=50000.0,
            market_cap_usd=900000000000.0,
            volume_24h_usd=1000000000.0,
            rank=1,
            percent_change_24h=2.5,
            source="test",
            source_id=str(uuid4())
        )
        test_db.add(sample_record)
        test_db.commit()
        
        response = test_client.get("/api/v1/data")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 1
        assert data["data"][0]["coin_id"] == "bitcoin"
        assert data["data"][0]["name"] == "Bitcoin"
        assert data["pagination"]["total_records"] == 1
    
    def test_get_data_pagination(self, test_client, test_db):
        """Test data endpoint pagination."""
        
        # Add multiple records
        for i in range(5):
            record = NormalizedCryptoData(
                coin_id=f"coin_{i}",
                name=f"Coin {i}",
                symbol=f"C{i}",
                price_usd=float(i * 1000),
                source="test",
                source_id=str(uuid4())
            )
            test_db.add(record)
        test_db.commit()
        
        # Test first page
        response = test_client.get("/api/v1/data?page=1&limit=2")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["total_records"] == 5
        assert data["pagination"]["total_pages"] == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is False
        
        # Test second page
        response = test_client.get("/api/v1/data?page=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data"]) == 2
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is True
    
    def test_get_data_filtering(self, test_client, test_db):
        """Test data endpoint filtering."""
        
        # Add records from different sources
        btc_record = NormalizedCryptoData(
            coin_id="bitcoin",
            name="Bitcoin",
            symbol="BTC",
            source="coinpaprika",
            source_id=str(uuid4())
        )
        eth_record = NormalizedCryptoData(
            coin_id="ethereum",
            name="Ethereum",
            symbol="ETH",
            source="coingecko",
            source_id=str(uuid4())
        )
        test_db.add_all([btc_record, eth_record])
        test_db.commit()
        
        # Test source filtering
        response = test_client.get("/api/v1/data?source=coinpaprika")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["source"] == "coinpaprika"
        
        # Test coin_id filtering
        response = test_client.get("/api/v1/data?coin_id=bitcoin")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["coin_id"] == "bitcoin"
        
        # Test symbol filtering
        response = test_client.get("/api/v1/data?symbol=ETH")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["symbol"] == "ETH"
    
    def test_get_data_invalid_params(self, test_client):
        """Test data endpoint with invalid parameters."""
        
        # Invalid page
        response = test_client.get("/api/v1/data?page=0")
        assert response.status_code == 422
        
        # Invalid limit
        response = test_client.get("/api/v1/data?limit=0")
        assert response.status_code == 422
        
        # Invalid source
        response = test_client.get("/api/v1/data?source=invalid_source")
        assert response.status_code == 400
    
    def test_get_data_summary(self, test_client, test_db):
        """Test data summary endpoint."""
        
        # Add sample data
        btc_record = NormalizedCryptoData(
            coin_id="bitcoin",
            name="Bitcoin",
            symbol="BTC",
            source="coinpaprika",
            source_id=str(uuid4())
        )
        eth_record = NormalizedCryptoData(
            coin_id="ethereum",
            name="Ethereum",
            symbol="ETH",
            source="coingecko",
            source_id=str(uuid4())
        )
        test_db.add_all([btc_record, eth_record])
        test_db.commit()
        
        response = test_client.get("/api/v1/data/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_records" in data
        assert "unique_coins" in data
        assert "records_by_source" in data
        assert "latest_updates" in data
        assert data["total_records"] == 2
        assert data["unique_coins"] == 2


class TestHealthEndpoint:
    """Test the /health endpoint."""
    
    def test_health_check_basic(self, test_client):
        """Test basic health check."""
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "database_connected" in data
        assert "version" in data
        assert data["database_connected"] is True
    
    def test_health_check_with_etl_run(self, test_client, test_db):
        """Test health check with ETL run data."""
        
        # Add sample ETL run
        etl_run = ETLRun(
            run_id="test_run_123",
            source="test_source",
            status="completed",
            records_processed=100,
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            duration_seconds=300.0
        )
        test_db.add(etl_run)
        test_db.commit()
        
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "etl_last_run" in data
        assert data["etl_last_run"] is not None
        assert data["etl_last_run"]["run_id"] == "test_run_123"
        assert data["etl_last_run"]["status"] == "completed"
    
    def test_detailed_health_check(self, test_client, test_db):
        """Test detailed health check endpoint."""
        
        response = test_client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert "basic_health" in data
        assert "database_stats" in data
        assert "etl_stats" in data
        assert "system_info" in data


class TestStatsEndpoint:
    """Test the /stats endpoint."""
    
    def test_stats_empty(self, test_client):
        """Test stats endpoint with no data."""
        response = test_client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_runs" in data
        assert "successful_runs" in data
        assert "failed_runs" in data
        assert "records_by_source" in data
        assert data["total_runs"] == 0
        assert data["successful_runs"] == 0
        assert data["failed_runs"] == 0
    
    def test_stats_with_runs(self, test_client, test_db):
        """Test stats endpoint with ETL runs."""
        
        # Add successful run
        successful_run = ETLRun(
            run_id="success_run",
            source="test_source",
            status="completed",
            records_processed=100,
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow() - timedelta(hours=1),
            duration_seconds=300.0
        )
        
        # Add failed run
        failed_run = ETLRun(
            run_id="failed_run",
            source="test_source",
            status="failed",
            records_processed=0,
            start_time=datetime.utcnow() - timedelta(hours=1),
            error_message="Test error"
        )
        
        test_db.add_all([successful_run, failed_run])
        test_db.commit()
        
        response = test_client.get("/api/v1/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_runs"] == 2
        assert data["successful_runs"] == 1
        assert data["failed_runs"] == 1
        assert data["last_successful_run"] is not None
        assert data["last_failed_run"] is not None
        assert data["avg_duration_seconds"] == 300.0
    
    def test_etl_runs_endpoint(self, test_client, test_db):
        """Test ETL runs listing endpoint."""
        
        # Add sample runs
        for i in range(3):
            run = ETLRun(
                run_id=f"run_{i}",
                source="test_source",
                status="completed",
                records_processed=i * 10,
                start_time=datetime.utcnow() - timedelta(hours=i),
                end_time=datetime.utcnow() - timedelta(hours=i-1) if i > 0 else datetime.utcnow(),
                duration_seconds=float(i * 100)
            )
            test_db.add(run)
        test_db.commit()
        
        response = test_client.get("/api/v1/stats/runs")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        assert all("run_id" in run for run in data)
        assert all("status" in run for run in data)
    
    def test_etl_runs_filtering(self, test_client, test_db):
        """Test ETL runs endpoint with filtering."""
        
        # Add runs with different sources and statuses
        coinpaprika_run = ETLRun(
            run_id="coinpaprika_run",
            source="coinpaprika",
            status="completed",
            start_time=datetime.utcnow()
        )
        
        coingecko_run = ETLRun(
            run_id="coingecko_run",
            source="coingecko",
            status="failed",
            start_time=datetime.utcnow()
        )
        
        test_db.add_all([coinpaprika_run, coingecko_run])
        test_db.commit()
        
        # Test source filtering
        response = test_client.get("/api/v1/stats/runs?source=coinpaprika")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "coinpaprika"
        
        # Test status filtering
        response = test_client.get("/api/v1/stats/runs?status=failed")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "failed"
        
        # Test invalid status
        response = test_client.get("/api/v1/stats/runs?status=invalid")
        assert response.status_code == 400
    
    def test_performance_stats(self, test_client, test_db):
        """Test performance statistics endpoint."""
        
        # Add recent runs
        recent_time = datetime.utcnow() - timedelta(hours=1)
        
        for i in range(3):
            run = ETLRun(
                run_id=f"recent_run_{i}",
                source="test_source",
                status="completed",
                records_processed=100,
                start_time=recent_time + timedelta(minutes=i*10),
                end_time=recent_time + timedelta(minutes=i*10+5),
                duration_seconds=300.0
            )
            test_db.add(run)
        test_db.commit()
        
        response = test_client.get("/api/v1/stats/performance?hours=24")
        assert response.status_code == 200
        
        data = response.json()
        assert "time_window_hours" in data
        assert "summary" in data
        assert "duration_stats" in data
        assert "by_source" in data
        assert data["summary"]["total_runs"] == 3
        assert data["summary"]["successful_runs"] == 3


class TestAPIMiddleware:
    """Test API middleware functionality."""
    
    def test_request_id_header(self, test_client):
        """Test that request ID is added to response headers."""
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_response_time_header(self, test_client):
        """Test that response time is added to headers."""
        response = test_client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        assert response.headers["X-Response-Time"].endswith("ms")
    
    def test_cors_headers(self, test_client):
        """Test CORS headers are present."""
        response = test_client.options("/api/v1/health")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers