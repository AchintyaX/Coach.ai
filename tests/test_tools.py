import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pydantic import ValidationError
import requests


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
def mock_athlete_data():
    """Mock athlete data for testing"""
    return {
        'id': 12345,
        'username': 'test_user',
        'firstname': 'John',
        'lastname': 'Doe',
        'city': 'Test City',
        'state': 'Test State',
        'country': 'Test Country',
        'sex': 'M',
        'weight': 70.0,
        'measurement_preference': 'meters',
        'premium': True,
        'summit': True,
        'created_at': '2020-01-01T00:00:00Z',
        'updated_at': '2023-01-01T00:00:00Z',
        'profile_medium': 'https://example.com/profile.jpg',
        'profile': 'https://example.com/profile_large.jpg'
    }


@pytest.fixture
def mock_activity_data():
    """Mock activity data for testing"""
    return [{
        'id': 12345,
        'name': 'Test Run',
        'distance': 5000.0,
        'start_date': '2023-09-26T10:00:00Z'
    }, {
        'id': 12346,
        'name': 'Test Ride',
        'distance': 15000.0,
        'start_date': '2023-09-25T09:00:00Z'
    }]


class TestGetAthleteProfile:
    """Test cases for get_athlete_profile tool"""
    
    def test_get_athlete_profile_success(self, mock_env, mock_athlete_data):
        """Test successful athlete profile retrieval"""
        from tools.get_athlete_profile import get_athlete_profile
        
        with patch('tools.get_athlete_profile.get_authenticated_athlete') as mock_get_athlete:
            # Create a mock athlete object with attributes
            mock_athlete = Mock()
            for key, value in mock_athlete_data.items():
                if key in ['created_at', 'updated_at']:
                    setattr(mock_athlete, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
                else:
                    setattr(mock_athlete, key, value)
            
            mock_get_athlete.return_value = mock_athlete
            
            result = get_athlete_profile()
            
            assert 'content' in result
            assert len(result['content']) == 1
            assert 'John Doe' in result['content'][0]['text']
            assert 'ID: 12345' in result['content'][0]['text']
            assert 'isError' not in result
    
    def test_get_athlete_profile_missing_token(self):
        """Test athlete profile with missing access token"""
        from tools.get_athlete_profile import get_athlete_profile
        
        with patch.dict(os.environ, {}, clear=True):
            result = get_athlete_profile()
            
            assert 'isError' in result
            assert result['isError'] is True
            assert 'Configuration Error' in result['content'][0]['text']
    
    def test_get_athlete_profile_api_error(self, mock_env):
        """Test athlete profile with API error"""
        from tools.get_athlete_profile import get_athlete_profile
        
        with patch('tools.get_athlete_profile.get_authenticated_athlete') as mock_get_athlete:
            mock_get_athlete.side_effect = requests.HTTPError("API Error")
            
            result = get_athlete_profile()
            
            assert 'isError' in result
            assert result['isError'] is True
            assert 'API Error' in result['content'][0]['text']


class TestGetRecentActivities:
    """Test cases for get_recent_activities tool"""
    
    def test_get_recent_activities_success(self, mock_env, mock_activity_data):
        """Test successful recent activities retrieval"""
        from tools.get_recent_activities import get_recent_activities_tool
        
        with patch('tools.get_recent_activities.get_recent_activities') as mock_get_activities:
            # Create mock activity objects
            mock_activities = []
            for activity_data in mock_activity_data:
                mock_activity = Mock()
                for key, value in activity_data.items():
                    if key == 'start_date':
                        setattr(mock_activity, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
                    else:
                        setattr(mock_activity, key, value)
                mock_activities.append(mock_activity)
            
            mock_get_activities.return_value = mock_activities
            
            result = get_recent_activities_tool(per_page=100)
            
            assert 'content' in result
            assert len(result['content']) == 2
            assert 'Test Run' in result['content'][0]['text']
            assert 'Test Ride' in result['content'][1]['text']
            assert 'isError' not in result
    
    def test_get_recent_activities_empty_result(self, mock_env):
        """Test recent activities with no results"""
        from tools.get_recent_activities import get_recent_activities_tool
        
        with patch('tools.get_recent_activities.get_recent_activities') as mock_get_activities:
            mock_get_activities.return_value = []
            
            result = get_recent_activities_tool()
            
            assert 'content' in result
            assert 'No recent activities found' in result['content'][0]['text']
    
    def test_get_recent_activities_missing_token(self):
        """Test recent activities with missing access token"""
        from tools.get_recent_activities import get_recent_activities_tool
        
        with patch.dict(os.environ, {}, clear=True):
            result = get_recent_activities_tool()
            
            assert 'isError' in result
            assert result['isError'] is True
            assert 'Configuration Error' in result['content'][0]['text']


class TestGetAthleteStats:
    """Test cases for get_athlete_stats tool"""
    
    def test_get_athlete_stats_success(self, mock_env):
        """Test successful athlete stats retrieval"""
        from tools.get_athlete_stats import get_athlete_stats_tool
        
        mock_stats_data = {
            'biggest_ride_distance': 100000.0,
            'biggest_climb_elevation_gain': 1500.0,
            'recent_ride_totals': {'count': 5, 'distance': 250000},
            'recent_run_totals': {'count': 10, 'distance': 50000},
            'recent_swim_totals': {'count': 2, 'distance': 2000},
            'ytd_ride_totals': {'count': 50, 'distance': 2500000},
            'ytd_run_totals': {'count': 100, 'distance': 500000},
            'ytd_swim_totals': {'count': 20, 'distance': 20000},
            'all_ride_totals': {'count': 200, 'distance': 10000000},
            'all_run_totals': {'count': 500, 'distance': 2500000},
            'all_swim_totals': {'count': 100, 'distance': 100000}
        }
        
        with patch('tools.get_athlete_stats.get_athlete_stats') as mock_get_stats:
            mock_stats = Mock()
            for key, value in mock_stats_data.items():
                setattr(mock_stats, key, value)
            mock_get_stats.return_value = mock_stats
            
            result = get_athlete_stats_tool(athlete_id=12345)
            
            assert 'content' in result
            assert 'Statistics for Athlete ID: 12345' in result['content'][0]['text']
            assert 'Biggest Ride Distance' in result['content'][0]['text']


class TestGetActivityDetails:
    """Test cases for get_activity_details tool"""
    
    def test_get_activity_details_success(self, mock_env):
        """Test successful activity details retrieval"""
        from tools.get_activity_details import get_activity_details
        
        mock_activity_detail = {
            'id': 12345,
            'name': 'Morning Run',
            'distance': 5000.0,
            'moving_time': 1800,
            'elapsed_time': 1900,
            'total_elevation_gain': 50.0,
            'type': 'Run',
            'start_date': '2023-09-26T06:00:00Z',
            'average_speed': 2.78,
            'max_speed': 4.5
        }
        
        with patch('strava_client.strava_api.get') as mock_api_get:
            mock_api_get.return_value = mock_activity_detail
            
            result = get_activity_details(activity_id=12345)
            
            assert 'content' in result
            assert 'Morning Run' in result['content'][0]['text']
            assert 'ID: 12345' in result['content'][0]['text']


class TestGetAthleteZones:
    """Test cases for get_athlete_zones tool"""
    
    def test_get_athlete_zones_success(self, mock_env):
        """Test successful athlete zones retrieval"""
        from tools.get_athlete_zones import get_athlete_zones
        
        mock_zones_data = {
            'heart_rate': {
                'custom_zones': True,
                'zones': [
                    {'min': 0, 'max': 142},
                    {'min': 142, 'max': 155},
                    {'min': 155, 'max': 169}
                ]
            },
            'power': {
                'zones': [
                    {'min': 0, 'max': 200},
                    {'min': 200, 'max': 250},
                    {'min': 250, 'max': 300}
                ]
            }
        }
        
        with patch('strava_client.strava_api.get') as mock_api_get:
            mock_api_get.return_value = mock_zones_data
            
            result = get_athlete_zones()
            
            assert 'content' in result
            assert 'Heart Rate Zones' in result['content'][0]['text']
            assert 'Power Zones' in result['content'][0]['text']


class TestGetActivityStreams:
    """Test cases for get_activity_streams tool"""
    
    def test_get_activity_streams_success(self, mock_env):
        """Test successful activity streams retrieval"""
        from tools.get_activity_streams import get_activity_streams
        
        mock_streams_data = [
            {
                'type': 'heartrate',
                'data': [120, 125, 130, 135, 140],
                'series_type': 'distance',
                'original_size': 5,
                'resolution': 'high'
            },
            {
                'type': 'latlng',
                'data': [[40.7128, -74.0060], [40.7129, -74.0061], [40.7130, -74.0062]],
                'series_type': 'distance',
                'original_size': 3,
                'resolution': 'high'
            }
        ]
        
        with patch('strava_client.strava_api.get') as mock_api_get:
            mock_api_get.return_value = mock_streams_data
            
            result = get_activity_streams(activity_id=12345, types=['heartrate', 'latlng'])
            
            assert 'content' in result
            assert 'Activity Streams for ID: 12345' in result['content'][0]['text']
            assert 'Heart Rate' in result['content'][0]['text']
            assert 'GPS Coordinates' in result['content'][0]['text']


@pytest.mark.integration
class TestToolsIntegration:
    """Integration tests for tools working together"""
    
    def test_athlete_profile_to_stats_workflow(self, mock_env, mock_athlete_data):
        """Test workflow from getting athlete profile to getting stats"""
        from tools.get_athlete_profile import get_athlete_profile
        from tools.get_athlete_stats import get_athlete_stats_tool
        
        with patch('tools.get_athlete_profile.get_authenticated_athlete') as mock_get_athlete:
            mock_athlete = Mock()
            mock_athlete.id = 12345
            mock_athlete.firstname = 'John'
            mock_athlete.lastname = 'Doe'
            mock_get_athlete.return_value = mock_athlete
            
            # Get athlete profile first
            profile_result = get_athlete_profile()
            assert 'ID: 12345' in profile_result['content'][0]['text']
            
            # Use athlete ID for stats
            with patch('tools.get_athlete_stats.get_athlete_stats') as mock_get_stats:
                mock_stats = Mock()
                mock_stats.recent_run_totals = {'count': 10, 'distance': 50000}
                mock_get_stats.return_value = mock_stats
                
                stats_result = get_athlete_stats_tool(athlete_id=12345)
                assert 'Statistics for Athlete ID: 12345' in stats_result['content'][0]['text']