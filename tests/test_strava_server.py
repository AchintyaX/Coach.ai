import importlib
import runpy

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import strava.strava_server


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    with patch.dict('os.environ', {
        'STRAVA_ACCESS_TOKEN': 'test_access_token',
        'STRAVA_REFRESH_TOKEN': 'test_refresh_token',
        'STRAVA_CLIENT_ID': '12345',
        'STRAVA_CLIENT_SECRET': 'test_secret'
    }):
        yield


@pytest.fixture
def mock_fastmcp():
    """Mock FastMCP server for testing.

    `strava.strava_server` builds its `mcp` instance (and registers tools)
    at import time via `create_server()`. To exercise that construction
    logic against a mock, we patch the *source* `fastmcp.FastMCP` (and
    `dotenv.load_dotenv`) and reload the module so its
    `from fastmcp import FastMCP` / `from dotenv import load_dotenv`
    statements pick up the mocks. The module is reloaded again afterwards
    (with the real `fastmcp`/`dotenv`) so other tests get the real server
    back.
    """
    with patch('fastmcp.FastMCP') as mock_mcp, patch('dotenv.load_dotenv'):
        mock_instance = Mock()
        mock_instance.tool = Mock(side_effect=lambda *args, **kwargs: (lambda fn: fn))
        mock_instance.run = Mock()
        mock_mcp.return_value = mock_instance

        importlib.reload(strava.strava_server)

        yield mock_instance

    # Restore the module to its real (production) state for subsequent tests.
    importlib.reload(strava.strava_server)


@pytest.fixture
def mock_tools():
    """Mock all tool functions"""
    with patch.multiple(
        'strava.strava_server',
        get_athlete_profile=Mock(return_value={'id': 12345, 'name': 'John Doe'}),
        get_athlete_stats_tool=Mock(return_value={'stats': 'test_stats'}),
        get_recent_activities_tool=Mock(return_value={'activities': 'test_activities'}),
        get_activity_details=Mock(return_value={'activity': 'test_activity'}),
        get_activity_streams=Mock(return_value={'streams': 'test_streams'}),
        get_athlete_zones=Mock(return_value={'zones': 'test_zones'})
    ) as mock_funcs:
        yield mock_funcs


class TestStravaServerInitialization:
    """Test Strava server initialization"""
    
    def test_fastmcp_server_creation(self, mock_env):
        """Test that FastMCP server is created correctly"""
        with patch('fastmcp.FastMCP') as mock_fastmcp, patch('dotenv.load_dotenv'):
            mock_instance = Mock()
            mock_instance.tool = Mock(side_effect=lambda *a, **k: (lambda fn: fn))
            mock_fastmcp.return_value = mock_instance

            # Reloading should trigger server creation
            importlib.reload(strava.strava_server)

            mock_fastmcp.assert_called_once_with(name="Strava Server")
            assert strava.strava_server.mcp == mock_instance

        importlib.reload(strava.strava_server)

    def test_dotenv_loading(self, mock_env):
        """Test that environment variables are loaded"""
        with patch('fastmcp.FastMCP') as mock_fastmcp, patch('dotenv.load_dotenv') as mock_load_dotenv:
            mock_instance = Mock()
            mock_instance.tool = Mock(side_effect=lambda *a, **k: (lambda fn: fn))
            mock_fastmcp.return_value = mock_instance

            importlib.reload(strava.strava_server)
            mock_load_dotenv.assert_called_once()

        importlib.reload(strava.strava_server)


class TestMCPToolRegistration:
    """Test MCP tool registration"""
    
    def test_get_athlete_profile_tool_registration(self, mock_env, mock_fastmcp):
        """Test athlete profile tool registration"""
        import strava.strava_server as strava_server
        
        # Check that tool decorator was called
        mock_fastmcp.tool.assert_called()
        
        # Get the decorator calls
        tool_calls = mock_fastmcp.tool.call_args_list
        
        # Find the get-athlete-profile tool call
        athlete_profile_call = None
        for call in tool_calls:
            if call[1].get('name') == 'get-athlete-profile':
                athlete_profile_call = call
                break
        
        assert athlete_profile_call is not None
        assert athlete_profile_call[1]['name'] == 'get-athlete-profile'
        assert 'profile information' in athlete_profile_call[1]['description']
    
    def test_get_athlete_stats_tool_registration(self, mock_env, mock_fastmcp):
        """Test athlete stats tool registration"""
        import strava.strava_server as strava_server
        
        tool_calls = mock_fastmcp.tool.call_args_list
        
        # Find the get-athlete-stats tool call
        athlete_stats_call = None
        for call in tool_calls:
            if call[1].get('name') == 'get-athlete-stats':
                athlete_stats_call = call
                break
        
        assert athlete_stats_call is not None
        assert athlete_stats_call[1]['name'] == 'get-athlete-stats'
        assert 'activity statistics' in athlete_stats_call[1]['description']
    
    def test_get_recent_activities_tool_registration(self, mock_env, mock_fastmcp):
        """Test recent activities tool registration"""
        import strava.strava_server as strava_server
        
        tool_calls = mock_fastmcp.tool.call_args_list
        
        # Find the get-recent-activities tool call
        recent_activities_call = None
        for call in tool_calls:
            if call[1].get('name') == 'get-recent-activities':
                recent_activities_call = call
                break
        
        assert recent_activities_call is not None
        assert recent_activities_call[1]['name'] == 'get-recent-activities'
        assert 'most recent activities' in recent_activities_call[1]['description']
    
    def test_get_activity_details_tool_registration(self, mock_env, mock_fastmcp):
        """Test activity details tool registration"""
        import strava.strava_server as strava_server
        
        tool_calls = mock_fastmcp.tool.call_args_list
        
        # Find the get-activity-details tool call
        activity_details_call = None
        for call in tool_calls:
            if call[1].get('name') == 'get-activity-details':
                activity_details_call = call
                break
        
        assert activity_details_call is not None
        assert activity_details_call[1]['name'] == 'get-activity-details'
        assert 'detailed information' in activity_details_call[1]['description']
    
    def test_get_activity_streams_tool_registration(self, mock_env, mock_fastmcp):
        """Test activity streams tool registration"""
        import strava.strava_server as strava_server
        
        tool_calls = mock_fastmcp.tool.call_args_list
        
        # Find the get-activity-streams tool call
        activity_streams_call = None
        for call in tool_calls:
            if call[1].get('name') == 'get-activity-streams':
                activity_streams_call = call
                break
        
        assert activity_streams_call is not None
        assert activity_streams_call[1]['name'] == 'get-activity-streams'
    
    def test_get_athlete_zones_tool_registration(self, mock_env, mock_fastmcp):
        """Test athlete zones tool registration"""
        import strava.strava_server as strava_server
        
        tool_calls = mock_fastmcp.tool.call_args_list
        
        # Find the get-athlete-zones tool call
        athlete_zones_call = None
        for call in tool_calls:
            if call[1].get('name') == 'get-athlete-zones':
                athlete_zones_call = call
                break
        
        assert athlete_zones_call is not None
        assert athlete_zones_call[1]['name'] == 'get-athlete-zones'
        assert 'heart rate and power zones' in athlete_zones_call[1]['description']


class TestMCPToolFunctions:
    """Test MCP tool function implementations"""
    
    def test_get_athlete_profile_tool_function(self, mock_env):
        """Test athlete profile tool function"""
        with patch('strava.strava_server.get_athlete_profile') as mock_get_profile:
            mock_get_profile.return_value = {'id': 12345, 'name': 'John Doe'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_athlete_profile_tool()
            
            mock_get_profile.assert_called_once()
            assert result == {'id': 12345, 'name': 'John Doe'}
    
    def test_get_athlete_stats_mcp_tool_function(self, mock_env):
        """Test athlete stats MCP tool function"""
        with patch('strava.strava_server.get_athlete_stats_tool') as mock_get_stats:
            mock_get_stats.return_value = {'stats': 'test_stats'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_athlete_stats_mcp_tool(athlete_id=12345)
            
            mock_get_stats.assert_called_once_with(athlete_id=12345)
            assert result == {'stats': 'test_stats'}
    
    def test_get_recent_activity_mcp_tool_function(self, mock_env):
        """Test recent activities MCP tool function"""
        with patch('strava.strava_server.get_recent_activities_tool') as mock_get_activities:
            mock_get_activities.return_value = {'activities': 'test_activities'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_recent_activity_mcp_tool(per_page=50)
            
            mock_get_activities.assert_called_once_with(per_page=50)
            assert result == {'activities': 'test_activities'}
    
    def test_get_recent_activity_mcp_tool_default_parameter(self, mock_env):
        """Test recent activities MCP tool function with default parameter"""
        with patch('strava.strava_server.get_recent_activities_tool') as mock_get_activities:
            mock_get_activities.return_value = {'activities': 'test_activities'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_recent_activity_mcp_tool()
            
            mock_get_activities.assert_called_once_with(per_page=100)
            assert result == {'activities': 'test_activities'}
    
    def test_get_activity_details_mcp_tool_function(self, mock_env):
        """Test activity details MCP tool function"""
        with patch('strava.strava_server.get_activity_details') as mock_get_details:
            mock_get_details.return_value = {'activity': 'test_activity'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_activity_details_mcp_tool(activity_id=67890)
            
            mock_get_details.assert_called_once_with(activity_id=67890)
            assert result == {'activity': 'test_activity'}
    
    def test_get_activity_streams_mcp_tool_function(self, mock_env):
        """Test activity streams MCP tool function"""
        with patch('strava.strava_server.get_activity_streams') as mock_get_streams:
            mock_get_streams.return_value = {'streams': 'test_streams'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_activity_streams_mcp_tool(
                activity_id=67890,
                types=['heartrate', 'latlng'],
                resolution='high',
                series_type='time'
            )
            
            mock_get_streams.assert_called_once_with(
                activity_id=67890,
                types=['heartrate', 'latlng']
            )
            assert result == {'streams': 'test_streams'}
    
    def test_get_activity_streams_mcp_tool_default_parameters(self, mock_env):
        """Test activity streams MCP tool function with default parameters"""
        with patch('strava.strava_server.get_activity_streams') as mock_get_streams:
            mock_get_streams.return_value = {'streams': 'test_streams'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_activity_streams_mcp_tool(activity_id=67890)
            
            mock_get_streams.assert_called_once_with(
                activity_id=67890,
                types=['latlng', 'altitude', 'heartrate', 'cadence', 'watts']
            )
            assert result == {'streams': 'test_streams'}
    
    def test_get_athlete_zones_mcp_tool_function(self, mock_env):
        """Test athlete zones MCP tool function"""
        with patch('strava.strava_server.get_athlete_zones') as mock_get_zones:
            mock_get_zones.return_value = {'zones': 'test_zones'}
            
            import strava.strava_server as strava_server
            result = strava_server.get_athlete_zones_mcp_tool()
            
            mock_get_zones.assert_called_once()
            assert result == {'zones': 'test_zones'}


class TestServerExecution:
    """Test server execution and main block"""
    
    def test_main_execution_sse_transport(self, mock_env):
        """Test main execution with SSE transport"""
        # Running the module as __main__ resets `__name__` on
        # `importlib.reload`, so execute the file directly via `runpy` with
        # the source FastMCP/dotenv patched, to exercise the
        # `if __name__ == "__main__":` block.
        with patch('fastmcp.FastMCP') as mock_fastmcp, patch('dotenv.load_dotenv'):
            mock_instance = Mock()
            mock_instance.tool = Mock(side_effect=lambda *a, **k: (lambda fn: fn))
            mock_instance.run = Mock()
            mock_fastmcp.return_value = mock_instance

            runpy.run_path('strava/strava_server.py', run_name='__main__')

            mock_instance.run.assert_called_with(transport="sse")

        importlib.reload(strava.strava_server)

    @patch('builtins.print')
    def test_server_startup_message(self, mock_print, mock_env):
        """Test server startup message is printed"""
        with patch('fastmcp.FastMCP') as mock_fastmcp, patch('dotenv.load_dotenv'):
            mock_instance = Mock()
            mock_instance.tool = Mock(side_effect=lambda *a, **k: (lambda fn: fn))
            mock_instance.run = Mock()
            mock_fastmcp.return_value = mock_instance

            runpy.run_path('strava/strava_server.py', run_name='__main__')

            # The print statement should be called when run as __main__
            mock_print.assert_any_call("🚀Starting server... ")

        importlib.reload(strava.strava_server)


@pytest.mark.integration
class TestStravaServerIntegration:
    """Integration tests for Strava server"""
    
    def test_full_server_initialization_flow(self, mock_env):
        """Test complete server initialization flow"""
        with patch('dotenv.load_dotenv') as mock_load_dotenv, \
             patch('fastmcp.FastMCP') as mock_fastmcp:

            mock_instance = Mock()
            mock_instance.tool = Mock(side_effect=lambda *a, **k: (lambda fn: fn))
            mock_fastmcp.return_value = mock_instance

            # Reloading should trigger full initialization
            importlib.reload(strava.strava_server)

            # Verify dotenv was loaded
            mock_load_dotenv.assert_called_once()

            # Verify FastMCP was initialized
            mock_fastmcp.assert_called_once_with(name="Strava Server")

            # Verify tools were registered (at least one)
            assert mock_instance.tool.call_count >= 6  # We have 6 tools

        importlib.reload(strava.strava_server)
    
    def test_tool_chain_execution(self, mock_env):
        """Test that tools can be executed in sequence"""
        with patch('strava.strava_server.get_athlete_profile') as mock_profile, \
             patch('strava.strava_server.get_athlete_stats_tool') as mock_stats:
            
            mock_profile.return_value = {'id': 12345, 'firstname': 'John', 'lastname': 'Doe'}
            mock_stats.return_value = {'recent_run_totals': {'count': 10}}
            
            import strava.strava_server as strava_server
            
            # Execute profile tool
            profile_result = strava_server.get_athlete_profile_tool()
            assert profile_result['id'] == 12345
            
            # Execute stats tool using profile ID
            stats_result = strava_server.get_athlete_stats_mcp_tool(athlete_id=12345)
            assert 'recent_run_totals' in stats_result
            
            # Verify both were called
            mock_profile.assert_called_once()
            mock_stats.assert_called_once_with(athlete_id=12345)