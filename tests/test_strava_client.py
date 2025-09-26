import pytest
import os
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pydantic import ValidationError
from strava_client import (
    StravaApiClient,
    StravaActivity,
    StravaAthlete,
    StravaStats,
    refresh_access_token,
    get_recent_activities,
    get_authenticated_athlete,
    get_athlete_stats,
    strava_api
)


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'STRAVA_ACCESS_TOKEN': 'test_access_token',
        'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
        'STRAVA_CLIENT_ID': '12345',
        'STRAVA_CLIENT_SECRET': 'test_secret'
    }):
        yield


@pytest.fixture
def sample_athlete_data():
    """Sample athlete data for testing"""
    return {
        'id': 12345,
        'username': 'test_user',
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
def sample_activity_data():
    """Sample activity data for testing"""
    return [
        {
            'id': 67890,
            'name': 'Morning Run',
            'distance': 5000.0,
            'start_date': '2023-09-26T06:00:00Z'
        },
        {
            'id': 67891,
            'name': 'Evening Bike Ride',
            'distance': 15000.0,
            'start_date': '2023-09-25T18:00:00Z'
        }
    ]


@pytest.fixture
def sample_stats_data():
    """Sample stats data for testing"""
    return {
        'biggest_ride_distance': 100000.0,
        'biggest_climb_elevation_gain': 1500.0,
        'recent_ride_totals': {'count': 5, 'distance': 250000, 'moving_time': 36000},
        'recent_run_totals': {'count': 10, 'distance': 50000, 'moving_time': 18000},
        'recent_swim_totals': {'count': 2, 'distance': 2000, 'moving_time': 3600},
        'ytd_ride_totals': {'count': 50, 'distance': 2500000, 'moving_time': 360000},
        'ytd_run_totals': {'count': 100, 'distance': 500000, 'moving_time': 180000},
        'ytd_swim_totals': {'count': 20, 'distance': 20000, 'moving_time': 36000},
        'all_ride_totals': {'count': 200, 'distance': 10000000, 'moving_time': 1800000},
        'all_run_totals': {'count': 500, 'distance': 2500000, 'moving_time': 900000},
        'all_swim_totals': {'count': 100, 'distance': 100000, 'moving_time': 180000}
    }


class TestStravaApiClient:
    """Test cases for StravaApiClient class"""
    
    def test_init(self):
        """Test StravaApiClient initialization"""
        client = StravaApiClient()
        assert client.BASE_URL == "https://www.strava.com/api/v3"
        assert hasattr(client, 'session')
        assert isinstance(client.session, requests.Session)
    
    @patch('requests.Session.get')
    def test_get_method_success(self, mock_get):
        """Test successful GET request"""
        mock_response = Mock()
        mock_response.json.return_value = {'test': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = StravaApiClient()
        result = client.get('test-endpoint', headers={'Authorization': 'Bearer token'})
        
        assert result == {'test': 'data'}
        mock_get.assert_called_once_with(
            'https://www.strava.com/api/v3/test-endpoint',
            headers={'Authorization': 'Bearer token'},
            params=None
        )
    
    @patch('requests.Session.get')
    def test_get_method_with_params(self, mock_get):
        """Test GET request with parameters"""
        mock_response = Mock()
        mock_response.json.return_value = {'test': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = StravaApiClient()
        result = client.get('test-endpoint', params={'per_page': 50})
        
        assert result == {'test': 'data'}
        mock_get.assert_called_once_with(
            'https://www.strava.com/api/v3/test-endpoint',
            headers=None,
            params={'per_page': 50}
        )
    
    @patch('requests.Session.get')
    def test_get_method_http_error(self, mock_get):
        """Test GET request with HTTP error"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        client = StravaApiClient()
        
        with pytest.raises(requests.HTTPError):
            client.get('test-endpoint')
    
    @patch('requests.Session.post')
    def test_post_method_success(self, mock_post):
        """Test successful POST request"""
        mock_response = Mock()
        mock_response.json.return_value = {'created': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = StravaApiClient()
        result = client.post('test-endpoint', data={'name': 'test'})
        
        assert result == {'created': 'data'}
        mock_post.assert_called_once_with(
            'https://www.strava.com/api/v3/test-endpoint',
            headers=None,
            json={'name': 'test'}
        )
    
    @patch('requests.Session.put')
    def test_put_method_success(self, mock_put):
        """Test successful PUT request"""
        mock_response = Mock()
        mock_response.json.return_value = {'updated': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response
        
        client = StravaApiClient()
        result = client.put('test-endpoint', data={'name': 'updated'})
        
        assert result == {'updated': 'data'}
        mock_put.assert_called_once_with(
            'https://www.strava.com/api/v3/test-endpoint',
            headers=None,
            json={'name': 'updated'}
        )


class TestPydanticModels:
    """Test cases for Pydantic models"""
    
    def test_strava_activity_model(self):
        """Test StravaActivity model validation"""
        activity_data = {
            'id': 12345,
            'name': 'Test Run',
            'distance': 5000.0,
            'start_date': '2023-09-26T06:00:00Z'
        }
        
        activity = StravaActivity(**activity_data)
        assert activity.id == 12345
        assert activity.name == 'Test Run'
        assert activity.distance == 5000.0
        assert isinstance(activity.start_date, datetime)
    
    def test_strava_activity_model_optional_id(self):
        """Test StravaActivity model with optional ID"""
        activity_data = {
            'name': 'Test Run',
            'distance': 5000.0,
            'start_date': '2023-09-26T06:00:00Z'
        }
        
        activity = StravaActivity(**activity_data)
        assert activity.id is None
        assert activity.name == 'Test Run'
    
    def test_strava_athlete_model(self, sample_athlete_data):
        """Test StravaAthlete model validation"""
        athlete = StravaAthlete(**sample_athlete_data)
        assert athlete.id == 12345
        assert athlete.firstname == 'John'
        assert athlete.lastname == 'Doe'
        assert athlete.premium is True
        assert isinstance(athlete.created_at, datetime)
    
    def test_strava_athlete_model_optional_fields(self):
        """Test StravaAthlete model with minimal required fields"""
        minimal_data = {
            'id': 12345,
            'firstname': 'John',
            'lastname': 'Doe',
            'premium': False,
            'summit': False,
            'created_at': '2020-01-01T00:00:00Z',
            'updated_at': '2023-01-01T00:00:00Z',
            'profile_medium': 'https://example.com/medium.jpg',
            'profile': 'https://example.com/profile.jpg'
        }
        
        athlete = StravaAthlete(**minimal_data)
        assert athlete.id == 12345
        assert athlete.username is None
        assert athlete.city is None
        assert athlete.weight is None
    
    def test_strava_stats_model(self, sample_stats_data):
        """Test StravaStats model validation"""
        stats = StravaStats(**sample_stats_data)
        assert stats.biggest_ride_distance == 100000.0
        assert stats.recent_run_totals['count'] == 10
        assert stats.ytd_ride_totals['distance'] == 2500000


class TestTokenRefresh:
    """Test cases for token refresh functionality"""
    
    @patch('requests.post')
    @patch('builtins.print')
    def test_refresh_access_token_success(self, mock_print, mock_post, mock_env):
        """Test successful token refresh"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_at': 1695728400  # Sample timestamp
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        new_token = refresh_access_token()
        
        assert new_token == 'new_access_token'
        assert os.environ['STRAVA_ACCESS_TOKEN'] == 'new_access_token'
        assert os.environ['STRAVA_REFRESH_TOKEN'] == 'new_refresh_token'
        
        mock_post.assert_called_once_with(
            "https://www.strava.com/oauth/token",
            json={
                "client_id": "12345",
                "client_secret": "test_secret",
                "refresh_token": "test_refresh_token",
                "grant_type": "refresh_token",
            }
        )
        mock_print.assert_called_once()
    
    def test_refresh_access_token_missing_credentials(self):
        """Test token refresh with missing credentials"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing refresh credentials"):
                refresh_access_token()
    
    @patch('requests.post')
    def test_refresh_access_token_http_error(self, mock_post, mock_env):
        """Test token refresh with HTTP error"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response
        
        with pytest.raises(requests.HTTPError):
            refresh_access_token()


class TestApiMethods:
    """Test cases for API methods"""
    
    @patch.object(strava_api, 'get')
    def test_get_recent_activities_success(self, mock_get, sample_activity_data):
        """Test successful recent activities retrieval"""
        mock_get.return_value = sample_activity_data
        
        activities = get_recent_activities('test_token', per_page=30)
        
        assert len(activities) == 2
        assert isinstance(activities[0], StravaActivity)
        assert activities[0].name == 'Morning Run'
        assert activities[1].name == 'Evening Bike Ride'
        
        mock_get.assert_called_once_with(
            "athlete/activities",
            headers={"Authorization": "Bearer test_token"},
            params={"per_page": 30}
        )
    
    @patch.object(strava_api, 'get')
    @patch('strava_client.refresh_access_token')
    def test_get_recent_activities_token_refresh(self, mock_refresh, mock_get, sample_activity_data):
        """Test recent activities with token refresh on 401 error"""
        # First call raises 401, second call succeeds
        mock_error = requests.HTTPError()
        mock_error.response = Mock()
        mock_error.response.status_code = 401
        
        mock_get.side_effect = [mock_error, sample_activity_data]
        mock_refresh.return_value = 'new_token'
        
        activities = get_recent_activities('expired_token', per_page=30)
        
        assert len(activities) == 2
        assert mock_get.call_count == 2
        mock_refresh.assert_called_once()
    
    @patch.object(strava_api, 'get')
    def test_get_recent_activities_validation_error(self, mock_get):
        """Test recent activities with invalid data"""
        mock_get.return_value = [{'invalid': 'data'}]  # Missing required fields
        
        with pytest.raises(ValidationError):
            get_recent_activities('test_token')
    
    @patch.object(strava_api, 'get')
    def test_get_authenticated_athlete_success(self, mock_get, sample_athlete_data):
        """Test successful authenticated athlete retrieval"""
        mock_get.return_value = sample_athlete_data
        
        athlete = get_authenticated_athlete('test_token')
        
        assert isinstance(athlete, StravaAthlete)
        assert athlete.id == 12345
        assert athlete.firstname == 'John'
        assert athlete.lastname == 'Doe'
        
        mock_get.assert_called_once_with(
            "athlete",
            headers={"Authorization": "Bearer test_token"}
        )
    
    @patch.object(strava_api, 'get')
    @patch('strava_client.refresh_access_token')
    def test_get_authenticated_athlete_token_refresh(self, mock_refresh, mock_get, sample_athlete_data):
        """Test authenticated athlete with token refresh on 401 error"""
        mock_error = requests.HTTPError()
        mock_error.response = Mock()
        mock_error.response.status_code = 401
        
        mock_get.side_effect = [mock_error, sample_athlete_data]
        mock_refresh.return_value = 'new_token'
        
        athlete = get_authenticated_athlete('expired_token')
        
        assert athlete.id == 12345
        assert mock_get.call_count == 2
        mock_refresh.assert_called_once()
    
    @patch.object(strava_api, 'get')
    def test_get_athlete_stats_success(self, mock_get, sample_stats_data):
        """Test successful athlete stats retrieval"""
        mock_get.return_value = sample_stats_data
        
        stats = get_athlete_stats('test_token', athlete_id=12345)
        
        assert isinstance(stats, StravaStats)
        assert stats.biggest_ride_distance == 100000.0
        assert stats.recent_run_totals['count'] == 10
        
        mock_get.assert_called_once_with(
            "athletes/12345/stats",
            headers={"Authorization": "Bearer test_token"}
        )
    
    @patch.object(strava_api, 'get')
    @patch('strava_client.refresh_access_token')
    def test_get_athlete_stats_token_refresh(self, mock_refresh, mock_get, sample_stats_data):
        """Test athlete stats with token refresh on 401 error"""
        mock_error = requests.HTTPError()
        mock_error.response = Mock()
        mock_error.response.status_code = 401
        
        mock_get.side_effect = [mock_error, sample_stats_data]
        mock_refresh.return_value = 'new_token'
        
        stats = get_athlete_stats('expired_token', athlete_id=12345)
        
        assert stats.biggest_ride_distance == 100000.0
        assert mock_get.call_count == 2
        mock_refresh.assert_called_once()
    
    @patch.object(strava_api, 'get')
    def test_get_athlete_stats_non_401_error(self, mock_get):
        """Test athlete stats with non-401 HTTP error"""
        mock_error = requests.HTTPError()
        mock_error.response = Mock()
        mock_error.response.status_code = 403  # Forbidden
        
        mock_get.side_effect = mock_error
        
        with pytest.raises(requests.HTTPError):
            get_athlete_stats('test_token', athlete_id=12345)


@pytest.mark.integration
class TestStravaClientIntegration:
    """Integration tests for Strava client functionality"""
    
    @patch.object(strava_api, 'get')
    def test_full_workflow_athlete_profile_to_stats(self, mock_get, sample_athlete_data, sample_stats_data):
        """Test complete workflow from athlete profile to stats"""
        # Setup mock responses
        mock_get.side_effect = [sample_athlete_data, sample_stats_data]
        
        # Get athlete profile
        athlete = get_authenticated_athlete('test_token')
        assert athlete.id == 12345
        
        # Get athlete stats using the ID
        stats = get_athlete_stats('test_token', athlete_id=athlete.id)
        assert stats.recent_run_totals['count'] == 10
        
        # Verify both API calls were made
        assert mock_get.call_count == 2
        mock_get.assert_any_call("athlete", headers={"Authorization": "Bearer test_token"})
        mock_get.assert_any_call("athletes/12345/stats", headers={"Authorization": "Bearer test_token"})
    
    @patch.object(strava_api, 'get')
    def test_error_handling_across_methods(self, mock_get):
        """Test consistent error handling across different methods"""
        mock_error = requests.HTTPError("500 Internal Server Error")
        mock_error.response = Mock()
        mock_error.response.status_code = 500
        
        mock_get.side_effect = mock_error
        
        # All methods should raise HTTPError for non-401 errors
        with pytest.raises(requests.HTTPError):
            get_authenticated_athlete('test_token')
        
        with pytest.raises(requests.HTTPError):
            get_recent_activities('test_token')
        
        with pytest.raises(requests.HTTPError):
            get_athlete_stats('test_token', athlete_id=12345)
    
    @patch('strava_client.refresh_access_token')
    @patch.object(strava_api, 'get')
    def test_token_refresh_consistency(self, mock_get, mock_refresh, sample_athlete_data):
        """Test that token refresh works consistently across all methods"""
        mock_error = requests.HTTPError()
        mock_error.response = Mock()
        mock_error.response.status_code = 401
        
        mock_get.side_effect = [mock_error, sample_athlete_data]
        mock_refresh.return_value = 'refreshed_token'
        
        # Test with get_authenticated_athlete
        athlete = get_authenticated_athlete('expired_token')
        assert athlete.id == 12345
        
        # Verify refresh was called and retry happened
        mock_refresh.assert_called_once()
        assert mock_get.call_count == 2