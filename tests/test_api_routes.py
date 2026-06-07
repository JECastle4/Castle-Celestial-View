"""
Integration tests for api/routes.py
"""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestDayOfWeekEndpoint:
    """Test cases for /api/v1/day-of-week endpoint"""
    
    def test_valid_request_date_only(self):
        """Test valid request with date only"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["day_of_week"] == 0
        assert data["day_name"] == "Sunday"
        assert "julian_date" in data
        assert isinstance(data["julian_date"], float)
        assert data["input_datetime"] == "2026-02-01T00:00:00Z"
    
    def test_valid_request_with_time(self):
        """Test valid request with both date and time"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01", "time": "14:30:45"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["day_of_week"] == 0
        assert data["day_name"] == "Sunday"
        assert data["input_datetime"] == "2026-02-01T14:30:45Z"
    
    def test_different_days_of_week(self):
        """Test multiple dates to verify different days"""
        test_cases = [
            ("2026-02-01", "Sunday", 0),
            ("2026-02-02", "Monday", 1),
            ("2026-02-03", "Tuesday", 2),
        ]
        
        for date, expected_name, expected_index in test_cases:
            response = client.post(
                "/api/v1/day-of-week",
                json={"date": date}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["day_name"] == expected_name
            assert data["day_of_week"] == expected_index
    
    def test_missing_date_field(self):
        """Test request without required date field"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"time": "12:00:00"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_date_format(self):
        """Test with invalid date format"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "not-a-date"}
        )
        
        assert response.status_code == 400
        assert "Invalid date/time format" in response.json()["detail"]
    
    def test_invalid_time_format(self):
        """Test with invalid time format"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01", "time": "not-a-time"}
        )
        
        assert response.status_code == 400
        assert "Invalid date/time format" in response.json()["detail"]
    
    def test_malformed_json(self):
        """Test with malformed JSON"""
        response = client.post(
            "/api/v1/day-of-week",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_empty_request_body(self):
        """Test with empty request body"""
        response = client.post(
            "/api/v1/day-of-week",
            json={}
        )
        
        assert response.status_code == 422
    
    def test_response_structure(self):
        """Test that response contains all required fields"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01", "time": "12:00:00"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present
        assert "julian_date" in data
        assert "day_of_week" in data
        assert "day_name" in data
        assert "input_datetime" in data
        
        # Verify types
        assert isinstance(data["julian_date"], float)
        assert isinstance(data["day_of_week"], int)
        assert isinstance(data["day_name"], str)
        assert isinstance(data["input_datetime"], str)
    
    def test_julian_date_increases_with_time(self):
        """Test that JD increases as time progresses through the day"""
        response1 = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01", "time": "00:00:00"}
        )
        response2 = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01", "time": "12:00:00"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        jd1 = response1.json()["julian_date"]
        jd2 = response2.json()["julian_date"]
        
        # JD at noon should be greater than JD at midnight
        assert jd2 > jd1
        # Should be approximately 0.5 days apart
        assert abs((jd2 - jd1) - 0.5) < 0.01


class TestMoonPhaseEndpoint:
    """Test cases for /api/v1/moon-phase endpoint"""
    
    def test_moon_phase_basic(self):
        """Test basic moon phase request"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "illumination" in data
        assert "phase_angle" in data
        assert "phase_name" in data
        assert "julian_date" in data
        assert "location" in data
        assert "input_datetime" in data
        
        assert isinstance(data["illumination"], float)
        assert isinstance(data["phase_angle"], float)
        assert isinstance(data["phase_name"], str)
        
        assert 0.0 <= data["illumination"] <= 1.0
        assert 0.0 <= data["phase_angle"] < 360.0
    
    def test_moon_phase_new_moon(self):
        """Test moon phase near new moon"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-29",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["illumination"] < 0.1
        assert "New Moon" in data["phase_name"]
    
    def test_moon_phase_full_moon(self):
        """Test moon phase near full moon"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-13",
                "time": "22:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["illumination"] > 0.9
        assert "Full Moon" in data["phase_name"]
    
    def test_moon_phase_default_elevation(self):
        """Test moon phase with default elevation"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["elevation"] == 0.0
    
    def test_moon_phase_invalid_date(self):
        """Test moon phase with invalid date"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "invalid-date",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 400
    
    def test_moon_phase_invalid_latitude(self):
        """Test moon phase with invalid latitude"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 100.0,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 422
    
    def test_moon_phase_invalid_longitude(self):
        """Test moon phase with invalid longitude"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": 200.0,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 422
    
    def test_moon_phase_name_values(self):
        """Test that phase name is valid"""
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        valid_names = [
            "New Moon",
            "Waxing Crescent",
            "First Quarter",
            "Waxing Gibbous",
            "Full Moon",
            "Waning Gibbous",
            "Last Quarter",
            "Waning Crescent",
        ]
        
        assert data["phase_name"] in valid_names


class TestHealthEndpoints:
    """Test health check and root endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns API info"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert data["health"] == "ok"
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"


class TestSunPositionEndpoint:
    """Test cases for /api/v1/sun-position endpoint"""
    
    def test_valid_request(self):
        """Test valid sun position request"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2026-02-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "altitude" in data
        assert "azimuth" in data
        assert "is_visible" in data
        assert "julian_date" in data
        assert "input_datetime" in data
        assert "location" in data
        
        assert isinstance(data["altitude"], float)
        assert isinstance(data["azimuth"], float)
        assert isinstance(data["is_visible"], bool)
        assert -90 <= data["altitude"] <= 90
        assert 0 <= data["azimuth"] < 360
    
    def test_request_without_elevation(self):
        """Test request with default elevation"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2026-02-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["elevation"] == 0.0
    
    def test_invalid_latitude(self):
        """Test with invalid latitude"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2026-02-01",
                "time": "12:00:00",
                "latitude": 91.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_longitude(self):
        """Test with invalid longitude"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2026-02-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 181.0
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_fields(self):
        """Test with missing required fields"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2026-02-01",
                "time": "12:00:00"
                # Missing latitude and longitude
            }
        )
        
        assert response.status_code == 422
    
    def test_invalid_date_format(self):
        """Test with invalid date format"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "not-a-date",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 400
        assert "Invalid input" in response.json()["detail"]
    
    def test_sun_visible_at_noon(self):
        """Test that sun is visible at noon"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2026-06-21",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_visible"] is True
        assert data["altitude"] > 0
    
    def test_sun_not_visible_at_midnight(self):
        """Test that sun is not visible at midnight"""
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2026-02-01",
                "time": "00:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_visible"] is False
        assert data["altitude"] < 0


class TestMoonPositionEndpoint:
    """Test cases for /api/v1/moon-position endpoint"""
    
    def test_moon_position_basic(self):
        """Test basic moon position request"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-01-15",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "altitude" in data
        assert "azimuth" in data
        assert "is_visible" in data
        assert "julian_date" in data
        assert "location" in data
        assert "input_datetime" in data
        
        assert isinstance(data["altitude"], float)
        assert isinstance(data["azimuth"], float)
        assert isinstance(data["is_visible"], bool)
        
        assert -90 <= data["altitude"] <= 90
        assert 0 <= data["azimuth"] <= 360
    
    def test_moon_position_default_elevation(self):
        """Test moon position with default elevation"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["elevation"] == 0.0
    
    def test_moon_position_southern_hemisphere(self):
        """Test moon position for southern hemisphere"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["latitude"] == -33.8688
        assert data["location"]["longitude"] == 151.2093
    
    def test_moon_position_visibility(self):
        """Test that moon visibility matches altitude"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["altitude"] > 0:
            assert data["is_visible"] is True
        else:
            assert data["is_visible"] is False
    
    def test_moon_position_invalid_date(self):
        """Test moon position with invalid date"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "invalid-date",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 400
    
    def test_moon_position_invalid_latitude(self):
        """Test moon position with invalid latitude"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 100.0,
                "longitude": -74.0060,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 422
    
    def test_moon_position_invalid_longitude(self):
        """Test moon position with invalid longitude"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": 200.0,
                "elevation": 0.0
            }
        )
        
        assert response.status_code == 422
    
    def test_moon_position_extreme_elevation(self):
        """Test moon position with Mt. Everest elevation"""
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-01-15",
                "time": "12:00:00",
                "latitude": 27.9881,
                "longitude": 86.9250,
                "elevation": 8848.86
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["elevation"] == 8848.86


class TestBatchEarthObservationsEndpoint:
    """Test cases for /api/v1/batch-earth-observations endpoint"""
    
    def test_valid_batch_request(self):
        """Test valid batch request with multiple frames"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "start_time": "12:00:00",
                "end_date": "2024-01-01",
                "end_time": "18:00:00",
                "frame_count": 7,
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check frames array
        assert "frames" in data
        assert len(data["frames"]) == 7
        
        # Check first frame structure
        first_frame = data["frames"][0]
        assert "datetime" in first_frame
        assert "sun" in first_frame
        assert "moon" in first_frame
        assert "moon_phase" in first_frame
        assert first_frame["datetime"] == "2024-01-01T12:00:00Z"
        
        # Check sun data structure
        assert "altitude" in first_frame["sun"]
        assert "azimuth" in first_frame["sun"]
        assert "is_visible" in first_frame["sun"]
        
        # Check moon data structure
        assert "altitude" in first_frame["moon"]
        assert "azimuth" in first_frame["moon"]
        assert "is_visible" in first_frame["moon"]
        
        # Check moon phase structure
        assert "illumination" in first_frame["moon_phase"]
        assert "phase_angle" in first_frame["moon_phase"]
        assert "phase_name" in first_frame["moon_phase"]
        
        # Check metadata
        assert "metadata" in data
        assert data["metadata"]["frame_count"] == 7
        assert data["metadata"]["start_datetime"] == "2024-01-01T12:00:00Z"
        assert data["metadata"]["end_datetime"] == "2024-01-01T18:00:00Z"
        assert data["metadata"]["time_span_hours"] == 6.0
        
        # Check last frame
        last_frame = data["frames"][-1]
        assert last_frame["datetime"] == "2024-01-01T18:00:00Z"
    
    def test_batch_with_default_times(self):
        """Test batch request with default start and end times"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "frame_count": 3,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Default start_time is 00:00:00, default end_time is 23:59:59
        assert data["frames"][0]["datetime"] == "2024-01-01T00:00:00Z"
        assert data["frames"][-1]["datetime"] == "2024-01-01T23:59:59Z"
    
    def test_batch_minimum_two_frames(self):
        """Test batch request with minimum frame count"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "start_time": "12:00:00",
                "end_date": "2024-01-01",
                "end_time": "13:00:00",
                "frame_count": 2,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["frames"]) == 2
    
    def test_batch_frame_count_too_low(self):
        """Test batch request with frame_count less than 2"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "frame_count": 1,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_batch_frame_count_too_high(self):
        """Test batch request with frame_count exceeding maximum"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
                "frame_count": 10001,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_batch_end_before_start(self):
        """Test batch request where end_date is before start_date"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-02",
                "end_date": "2024-01-01",
                "frame_count": 2,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 400
        assert "end_datetime must be after start_datetime" in response.json()["detail"]
    
    def test_batch_equal_start_end(self):
        """Test batch request where start and end times are equal"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "start_time": "12:00:00",
                "end_date": "2024-01-01",
                "end_time": "12:00:00",
                "frame_count": 2,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 400
        assert "end_datetime must be after start_datetime" in response.json()["detail"]
    
    def test_batch_invalid_latitude(self):
        """Test batch request with invalid latitude"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "end_time": "13:00:00",
                "frame_count": 2,
                "latitude": 91.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_batch_invalid_longitude(self):
        """Test batch request with invalid longitude"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "end_time": "13:00:00",
                "frame_count": 2,
                "latitude": 0.0,
                "longitude": 181.0
            }
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_batch_invalid_date_format(self):
        """Test batch request with invalid date format"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "01-01-2024",
                "end_date": "2024-01-02",
                "frame_count": 2,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_batch_missing_required_fields(self):
        """Test batch request with missing required fields"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "frame_count": 2
                # Missing end_date, latitude, longitude
            }
        )
        
        assert response.status_code == 422
    
    def test_batch_multi_day_span(self):
        """Test batch calculation spanning multiple days"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "start_time": "12:00:00",
                "end_date": "2024-01-03",
                "end_time": "12:00:00",
                "frame_count": 3,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["frames"]) == 3
        assert data["frames"][0]["datetime"] == "2024-01-01T12:00:00Z"
        assert data["frames"][1]["datetime"] == "2024-01-02T12:00:00Z"
        assert data["frames"][2]["datetime"] == "2024-01-03T12:00:00Z"
        assert data["metadata"]["time_span_hours"] == 48.0
    
    def test_batch_negative_elevation(self):
        """Test batch with negative elevation (below sea level)"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "start_time": "12:00:00",
                "end_date": "2024-01-01",
                "end_time": "13:00:00",
                "frame_count": 2,
                "latitude": 31.5,
                "longitude": 35.5,
                "elevation": -430.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["location"]["elevation"] == -430.0
    
    def test_batch_high_elevation(self):
        """Test batch with high elevation (Mt. Everest)"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "start_time": "12:00:00",
                "end_date": "2024-01-01",
                "end_time": "13:00:00",
                "frame_count": 2,
                "latitude": 27.9881,
                "longitude": 86.9250,
                "elevation": 8848.86
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["location"]["elevation"] == 8848.86
    
    def test_batch_location_metadata(self):
        """Test that location metadata is correctly returned"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
                "end_time": "01:00:00",
                "frame_count": 2,
                "latitude": 51.5074,
                "longitude": -0.1278,
                "elevation": 11.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["metadata"]["location"]["latitude"] == 51.5074
        assert data["metadata"]["location"]["longitude"] == -0.1278
        assert data["metadata"]["location"]["elevation"] == 11.0
    
    def test_batch_frame_intervals(self):
        """Test that frames are evenly spaced"""
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2024-01-01",
                "start_time": "00:00:00",
                "end_date": "2024-01-01",
                "end_time": "04:00:00",
                "frame_count": 5,
                "latitude": 0.0,
                "longitude": 0.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check frames are evenly spaced at 1 hour intervals
        assert data["frames"][0]["datetime"] == "2024-01-01T00:00:00Z"
        assert data["frames"][1]["datetime"] == "2024-01-01T01:00:00Z"
        assert data["frames"][2]["datetime"] == "2024-01-01T02:00:00Z"
        assert data["frames"][3]["datetime"] == "2024-01-01T03:00:00Z"
        assert data["frames"][4]["datetime"] == "2024-01-01T04:00:00Z"


class TestAcceptLanguage:
    """Tests for Accept-Language header locale negotiation via middleware."""

    # --- day_name is a localised string returned by dates service ---

    def test_no_header_returns_english(self):
        """Requests without Accept-Language default to English."""
        response = client.post("/api/v1/day-of-week", json={"date": "2026-02-01"})
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

    def test_explicit_en_returns_english(self):
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "en"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

    def test_browser_style_header_returns_english(self):
        """Parses real-world browser Accept-Language with quality values."""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

    def test_reverse_locale_reverses_day_name(self):
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "xx-reverse"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"[::-1]

    def test_unsupported_locale_falls_back_to_english(self):
        """An unrecognised locale (e.g. 'fr') silently falls back to English."""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "fr"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

    # --- phase_name is a localised string returned by moon_phase service ---

    def test_reverse_locale_reverses_moon_phase_name(self):
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-01-13",
                "time": "22:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
            headers={"Accept-Language": "xx-reverse"},
        )
        assert response.status_code == 200
        phase = response.json()["phase_name"]
        # 2025-01-13 22:00 UTC is a Full Moon; xx-reverse reverses each character
        assert phase == "Full Moon"[::-1]

    # --- ?lang= query parameter (SSE fallback, EventSource can't set headers) ---

    def test_lang_query_param_reverses_day_name(self):
        """?lang=xx-reverse is honoured when no Accept-Language header is present."""
        response = client.post(
            "/api/v1/day-of-week?lang=xx-reverse",
            json={"date": "2026-02-01"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"[::-1]

    def test_lang_query_param_unsupported_falls_back_to_english(self):
        """?lang=fr falls back to English."""
        response = client.post(
            "/api/v1/day-of-week?lang=fr",
            json={"date": "2026-02-01"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

    def test_lang_param_takes_priority_over_accept_language_header(self):
        """When both ?lang= and Accept-Language header are present, ?lang= wins.
        This matters for SSE: EventSource always sends the browser's Accept-Language
        header, so ?lang= must override it."""
        response = client.post(
            "/api/v1/day-of-week?lang=xx-reverse",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "en"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"[::-1]

    def test_second_preference_used_when_first_unsupported(self):
        """fr, xx-reverse;q=0.9 — first preference unsupported, second is picked."""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "fr, xx-reverse;q=0.9"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"[::-1]


class TestExceptionHandling:
    """Test exception handling across all routes"""
    
    def test_day_of_week_value_error(self):
        """Test ValueError handling in day-of-week endpoint"""
        from unittest.mock import patch
        
        with patch("api.routes.calculate_day_of_week") as mock_calc:
            mock_calc.side_effect = ValueError("Test calculation error")
            
            response = client.post(
                "/api/v1/day-of-week",
                json={"date": "2026-02-01"}
            )
            
            assert response.status_code == 400
            assert "Invalid date/time format" in response.json()["detail"]
    
    def test_sun_position_value_error(self):
        """Test ValueError handling in sun-position endpoint"""
        from unittest.mock import patch
        
        with patch("api.routes.calculate_sun_position") as mock_calc:
            mock_calc.side_effect = ValueError("Test calculation error")
            
            response = client.post(
                "/api/v1/sun-position",
                json={
                    "date": "2026-06-01",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                }
            )
            
            assert response.status_code == 400
            assert "Invalid input" in response.json()["detail"]
    
    def test_moon_position_value_error(self):
        """Test ValueError handling in moon-position endpoint"""
        from unittest.mock import patch
        
        with patch("api.routes.calculate_moon_position") as mock_calc:
            mock_calc.side_effect = ValueError("Test calculation error")
            
            response = client.post(
                "/api/v1/moon-position",
                json={
                    "date": "2026-06-01",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                }
            )
            
            assert response.status_code == 400
            assert "Invalid input" in response.json()["detail"]
    
    def test_moon_phase_value_error(self):
        """Test ValueError handling in moon-phase endpoint"""
        from unittest.mock import patch
        
        with patch("api.routes.calculate_moon_phase") as mock_calc:
            mock_calc.side_effect = ValueError("Test calculation error")
            
            response = client.post(
                "/api/v1/moon-phase",
                json={
                    "date": "2026-06-01",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                }
            )
            
            assert response.status_code == 400
            assert "Invalid input" in response.json()["detail"]
    
    def test_batch_earth_observations_value_error(self):
        """Test ValueError handling in batch-earth-observations endpoint"""
        from unittest.mock import patch
        
        with patch("api.routes.calculate_batch_earth_observations") as mock_calc:
            mock_calc.side_effect = ValueError("Test calculation error")
            
            response = client.post(
                "/api/v1/batch-earth-observations",
                json={
                    "start_date": "2026-06-01",
                    "start_time": "12:00:00",
                    "end_date": "2026-06-02",
                    "end_time": "12:00:00",
                    "frame_count": 5,
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                }
            )
            
            assert response.status_code == 400
            assert "Invalid input" in response.json()["detail"]

    def test_prefix_match_on_second_preference(self):
        """fr-CA, en;q=0.8 — fr-CA unsupported, 'en' prefix-matches on second tag."""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "fr-CA, en;q=0.8"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

    def test_q0_excluded_so_lower_preference_wins(self):
        """xx-reverse;q=0 is not acceptable; valid lower-preference 'en' wins."""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "xx-reverse;q=0, en;q=0.5"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

    def test_bogus_q_treated_as_not_acceptable(self):
        """xx-reverse;q=bogus is skipped; valid lower-preference 'en' wins."""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "xx-reverse;q=bogus, en;q=0.9"},
        )
        assert response.status_code == 200
        assert response.json()["day_name"] == "Sunday"

