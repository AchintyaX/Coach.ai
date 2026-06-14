"""
Shared pytest fixtures and configuration for Coach AI tests
"""
import pytest
import os
from unittest.mock import Mock, patch
from datetime import datetime


@pytest.fixture(scope="session")
def test_env_vars():
    """Session-scoped environment variables for testing"""
    return {
        'AZURE_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_API_KEY': 'test_azure_key',
        'AZURE_DEPLOYMENT_NAME': 'gpt-4',
        'AZURE_MODEL_NAME': 'gpt-4',
        'AZURE_API_VERSION': '2024-12-01-preview',
        'TAVILY_API_KEY': 'test_tavily_key',
        'STRAVA_ACCESS_TOKEN': 'test_access_token',
        'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
        'STRAVA_CLIENT_ID': '12345',
        'STRAVA_CLIENT_SECRET': 'test_secret',
        'ROUTE_EXPORT_PATH': './test-exports'
    }


@pytest.fixture
def clean_env(test_env_vars):
    """Clean environment with test variables"""
    with patch.dict(os.environ, test_env_vars, clear=True):
        yield test_env_vars


@pytest.fixture
def sample_athlete():
    """Sample athlete data for testing"""
    return {
        'id': 12345,
        'username': 'test_athlete',
        'firstname': 'John',
        'lastname': 'Doe',
        'city': 'San Francisco',
        'state': 'CA',
        'country': 'USA',
        'sex': 'M',
        'premium': True,
        'summit': True,
        'created_at': '2020-01-01T00:00:00Z',
        'updated_at': '2023-01-01T00:00:00Z',
        'profile_medium': 'https://example.com/profile_medium.jpg',
        'profile': 'https://example.com/profile.jpg',
        'weight': 70.5,
        'measurement_preference': 'meters'
    }


@pytest.fixture
def sample_activities():
    """Sample activities data for testing"""
    return [
        {
            'id': 67890,
            'name': 'Morning Run',
            'distance': 5000.0,
            'start_date': '2023-09-26T06:00:00Z',
            'moving_time': 1800,
            'elapsed_time': 1900,
            'total_elevation_gain': 50.0,
            'type': 'Run'
        },
        {
            'id': 67891,
            'name': 'Evening Bike Ride',
            'distance': 15000.0,
            'start_date': '2023-09-25T18:00:00Z',
            'moving_time': 3600,
            'elapsed_time': 3700,
            'total_elevation_gain': 200.0,
            'type': 'Ride'
        }
    ]


@pytest.fixture
def sample_stats():
    """Sample stats data for testing"""
    return {
        'biggest_ride_distance': 100000.0,
        'biggest_climb_elevation_gain': 1500.0,
        'recent_ride_totals': {
            'count': 5,
            'distance': 250000,
            'moving_time': 36000,
            'elevation_gain': 2500
        },
        'recent_run_totals': {
            'count': 10,
            'distance': 50000,
            'moving_time': 18000,
            'elevation_gain': 500
        },
        'recent_swim_totals': {
            'count': 2,
            'distance': 2000,
            'moving_time': 3600,
            'elevation_gain': 0
        },
        'ytd_ride_totals': {
            'count': 50,
            'distance': 2500000,
            'moving_time': 360000,
            'elevation_gain': 25000
        },
        'ytd_run_totals': {
            'count': 100,
            'distance': 500000,
            'moving_time': 180000,
            'elevation_gain': 5000
        },
        'ytd_swim_totals': {
            'count': 20,
            'distance': 20000,
            'moving_time': 36000,
            'elevation_gain': 0
        },
        'all_ride_totals': {
            'count': 200,
            'distance': 10000000,
            'moving_time': 1800000,
            'elevation_gain': 100000
        },
        'all_run_totals': {
            'count': 500,
            'distance': 2500000,
            'moving_time': 900000,
            'elevation_gain': 25000
        },
        'all_swim_totals': {
            'count': 100,
            'distance': 100000,
            'moving_time': 180000,
            'elevation_gain': 0
        }
    }


@pytest.fixture
def mock_strava_athlete(sample_athlete):
    """Mock Strava athlete object"""
    athlete = Mock()
    for key, value in sample_athlete.items():
        if key in ['created_at', 'updated_at']:
            setattr(athlete, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
        else:
            setattr(athlete, key, value)
    return athlete


@pytest.fixture
def mock_strava_activities(sample_activities):
    """Mock Strava activities list"""
    activities = []
    for activity_data in sample_activities:
        activity = Mock()
        for key, value in activity_data.items():
            if key == 'start_date':
                setattr(activity, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
            else:
                setattr(activity, key, value)
        activities.append(activity)
    return activities


@pytest.fixture
def mock_strava_stats(sample_stats):
    """Mock Strava stats object"""
    stats = Mock()
    for key, value in sample_stats.items():
        setattr(stats, key, value)
    return stats


# Utility functions for tests
def create_mock_response(status_code=200, json_data=None, headers=None):
    """Create a mock HTTP response"""
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = json_data or {}
    response.raise_for_status = Mock()
    if status_code >= 400:
        from requests import HTTPError
        response.raise_for_status.side_effect = HTTPError(f"{status_code} Error")
    return response


def create_mock_http_error(status_code=401, message="HTTP Error"):
    """Create a mock HTTP error"""
    from requests import HTTPError
    error = HTTPError(message)
    error.response = Mock()
    error.response.status_code = status_code
    return error


# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow