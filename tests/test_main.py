import pytest
import asyncio
import os
import subprocess
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from main import (
    load_tools,
    load_llm,
    create_agent,
    create_memory,
    check_mcp_server,
    start_mcp_server,
    main
)


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'AZURE_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_API_KEY': 'test_azure_key',
        'AZURE_DEPLOYMENT_NAME': 'gpt-4',
        'AZURE_MODEL_NAME': 'gpt-4',
        'AZURE_API_VERSION': '2024-12-01-preview',
        'TAVILY_API_KEY': 'test_tavily_key',
        'STRAVA_CLIENT_ID': '12345'
    }):
        yield


@pytest.fixture
def mock_tools():
    """Mock tools for testing"""
    mock_tool1 = Mock()
    mock_tool1.metadata.name = "test_tool_1"
    mock_tool1.metadata.description = "Test tool 1 description"
    
    mock_tool2 = Mock()
    mock_tool2.metadata.name = "test_tool_2"
    mock_tool2.metadata.description = "Test tool 2 description"
    
    return [mock_tool1, mock_tool2]


class TestLoadTools:
    """Test cases for load_tools function"""
    
    @pytest.mark.asyncio
    async def test_load_tools_success(self, mock_env):
        """Test successful loading of both Strava and Tavily tools"""
        mock_strava_tools = [Mock(), Mock()]
        mock_strava_tools[0].metadata.name = "strava_tool"
        mock_strava_tools[0].metadata.description = "Strava tool description"
        
        mock_tavily_tools = [Mock()]
        mock_tavily_tools[0].metadata.name = "tavily_search"
        mock_tavily_tools[0].metadata.description = "Tavily search description"
        
        with patch('main.BasicMCPClient') as mock_mcp_client, \
             patch('main.McpToolSpec') as mock_mcp_tool_spec, \
             patch('main.logger'):
            
            # Setup Strava MCP mock
            mock_strava_client = Mock()
            mock_strava_tool_spec = Mock()
            mock_strava_tool_spec.to_tool_list_async = AsyncMock(return_value=mock_strava_tools)
            
            # Setup Tavily MCP mock
            mock_tavily_client = Mock()
            mock_tavily_tool_spec = Mock()
            mock_tavily_tool_spec.to_tool_list_async = AsyncMock(return_value=mock_tavily_tools)
            
            # Configure mocks
            mock_mcp_client.side_effect = [mock_strava_client, mock_tavily_client]
            mock_mcp_tool_spec.side_effect = [mock_strava_tool_spec, mock_tavily_tool_spec]
            
            result = await load_tools()
            
            assert len(result) == 3  # 2 Strava + 1 Tavily
            assert result == mock_strava_tools + mock_tavily_tools
            
            # Verify Strava MCP client was created correctly
            mock_mcp_client.assert_any_call("http://127.0.0.1:8000/sse")
            
            # Verify Tavily MCP client was created correctly
            mock_mcp_client.assert_any_call("https://mcp.tavily.com/mcp/?tavilyApiKey=test_tavily_key")
    
    @pytest.mark.asyncio
    async def test_load_tools_missing_tavily_key(self):
        """Test load_tools with missing Tavily API key"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': ''}, clear=False):
            with patch('main.BasicMCPClient') as mock_mcp_client:
                mock_mcp_client.side_effect = [Mock(), Mock()]
                
                with patch('main.McpToolSpec') as mock_mcp_tool_spec:
                    mock_tool_spec = Mock()
                    mock_tool_spec.to_tool_list_async = AsyncMock(return_value=[])
                    mock_mcp_tool_spec.return_value = mock_tool_spec
                    
                    result = await load_tools()
                    
                    # Should still work but with empty string in URL
                    mock_mcp_client.assert_any_call("https://mcp.tavily.com/mcp/?tavilyApiKey=")
    
    @pytest.mark.asyncio
    async def test_load_tools_with_logging(self, mock_env, mock_tools):
        """Test that tools are properly logged"""
        with patch('main.BasicMCPClient'), \
             patch('main.McpToolSpec') as mock_mcp_tool_spec, \
             patch('main.logger') as mock_logger:
            
            mock_tool_spec = Mock()
            mock_tool_spec.to_tool_list_async = AsyncMock(return_value=mock_tools)
            mock_mcp_tool_spec.return_value = mock_tool_spec
            
            await load_tools()
            
            # Verify logging calls
            assert mock_logger.info.call_count == len(mock_tools) * 2  # Called for each tool from both clients
            mock_logger.info.assert_any_call("Tool Name - test_tool_1\n Tool Description - Test tool 1 description")


class TestLoadLLM:
    """Test cases for load_llm function"""
    
    def test_load_llm_success(self, mock_env):
        """Test successful LLM loading"""
        with patch('main.AzureOpenAI') as mock_azure_openai:
            mock_llm = Mock()
            mock_azure_openai.return_value = mock_llm
            
            result = load_llm()
            
            assert result == mock_llm
            mock_azure_openai.assert_called_once_with(
                model='gpt-4',
                deployment_name='gpt-4',
                api_key='test_azure_key',
                azure_endpoint='https://test.openai.azure.com/',
                api_version='2024-12-01-preview',
                temperature=0.0
            )
    
    def test_load_llm_missing_env_vars(self):
        """Test LLM loading with missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('main.AzureOpenAI') as mock_azure_openai:
                load_llm()
                
                # Should still call AzureOpenAI but with None values
                mock_azure_openai.assert_called_once_with(
                    model=None,
                    deployment_name=None,
                    api_key=None,
                    azure_endpoint=None,
                    api_version=None,
                    temperature=0.0
                )


class TestCreateAgent:
    """Test cases for create_agent function"""
    
    def test_create_agent_success(self, mock_tools):
        """Test successful agent creation"""
        mock_llm = Mock()
        
        with patch('main.ReActAgent') as mock_react_agent, \
             patch('main.PromptTemplate') as mock_prompt_template, \
             patch('main.FITNESS_COACH_SYSTEM_PROMPT', 'Test prompt'):
            
            mock_agent = Mock()
            mock_react_agent.return_value = mock_agent
            mock_template = Mock()
            mock_prompt_template.return_value = mock_template
            
            result = create_agent(mock_tools, mock_llm)
            
            assert result == mock_agent
            mock_react_agent.assert_called_once_with(
                tools=mock_tools,
                llm=mock_llm,
                verbose=True
            )
            mock_prompt_template.assert_called_once_with('Test prompt')
            mock_agent.update_prompts.assert_called_once_with({"react_header": mock_template})


class TestCreateMemory:
    """Test cases for create_memory function"""
    
    def test_create_memory_success(self):
        """Test successful memory creation"""
        with patch('main.Memory') as mock_memory:
            mock_memory_instance = Mock()
            mock_memory.from_defaults.return_value = mock_memory_instance
            
            result = create_memory()
            
            assert result == mock_memory_instance
            mock_memory.from_defaults.assert_called_once_with(
                session_id="strava_coach_session",
                token_limit=40000
            )


class TestCheckMCPServer:
    """Test cases for check_mcp_server function"""
    
    @patch('requests.get')
    def test_check_mcp_server_success_200(self, mock_get):
        """Test MCP server check with 200 status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_mcp_server()
        
        assert result is True
        mock_get.assert_called_once_with("http://127.0.0.1:8000/sse", timeout=5, stream=True)
    
    @patch('requests.get')
    def test_check_mcp_server_success_204(self, mock_get):
        """Test MCP server check with 204 status"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_get.return_value = mock_response
        
        result = check_mcp_server()
        
        assert result is True
    
    @patch('requests.get')
    def test_check_mcp_server_success_sse_content_type(self, mock_get):
        """Test MCP server check with SSE content type"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {'content-type': 'text/event-stream'}
        mock_get.return_value = mock_response
        
        result = check_mcp_server()
        
        assert result is True
    
    @patch('requests.get')
    def test_check_mcp_server_failure(self, mock_get):
        """Test MCP server check failure"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        result = check_mcp_server()
        
        assert result is False
    
    @patch('requests.get')
    def test_check_mcp_server_connection_error(self, mock_get):
        """Test MCP server check with connection error"""
        mock_get.side_effect = requests.ConnectionError()
        
        result = check_mcp_server()
        
        assert result is False


class TestStartMCPServer:
    """Test cases for start_mcp_server function"""
    
    @patch('main.check_mcp_server')
    @patch('main.time.sleep')
    @patch('subprocess.Popen')
    @patch('main.logger')
    def test_start_mcp_server_success(self, mock_logger, mock_popen, mock_sleep, mock_check):
        """Test successful MCP server start"""
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_check.return_value = True  # Server starts successfully
        
        result = start_mcp_server()
        
        assert result == mock_process
        mock_popen.assert_called_once_with(
            ["uv", "run", "python", "strava_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        mock_logger.info.assert_any_call("Starting MCP Strava server...")
        mock_logger.info.assert_any_call("MCP Strava server started successfully")
    
    @patch('main.check_mcp_server')
    @patch('main.time.sleep')
    @patch('subprocess.Popen')
    @patch('main.logger')
    def test_start_mcp_server_timeout(self, mock_logger, mock_popen, mock_sleep, mock_check):
        """Test MCP server start timeout"""
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_check.return_value = False  # Server never starts
        
        result = start_mcp_server()
        
        assert result is None
        mock_logger.error.assert_called_with("Failed to start MCP Strava server after waiting")
    
    @patch('subprocess.Popen')
    @patch('main.logger')
    def test_start_mcp_server_exception(self, mock_logger, mock_popen):
        """Test MCP server start with exception"""
        mock_popen.side_effect = Exception("Test error")
        
        result = start_mcp_server()
        
        assert result is None
        mock_logger.error.assert_called_with("Error starting MCP Strava server: Test error")


class TestMainFunction:
    """Test cases for main function"""
    
    @pytest.mark.asyncio
    async def test_main_server_already_running(self, mock_env):
        """Test main function when server is already running"""
        with patch('main.check_mcp_server', return_value=True), \
             patch('main.load_tools') as mock_load_tools, \
             patch('main.load_llm') as mock_load_llm, \
             patch('main.create_agent') as mock_create_agent, \
             patch('main.create_memory') as mock_create_memory, \
             patch('main.logger') as mock_logger, \
             patch('builtins.input', side_effect=['quit']), \
             patch('builtins.print'):
            
            mock_tools = [Mock()]
            mock_llm = Mock()
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value="Test response")
            mock_memory = Mock()
            
            mock_load_tools.return_value = mock_tools
            mock_load_llm.return_value = mock_llm
            mock_create_agent.return_value = mock_agent
            mock_create_memory.return_value = mock_memory
            
            await main()
            
            mock_logger.info.assert_called_with("MCP Strava server is already running")
            mock_load_tools.assert_called_once()
            mock_load_llm.assert_called_once()
            mock_create_agent.assert_called_once_with(mock_tools, mock_llm)
            mock_create_memory.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_start_server(self, mock_env):
        """Test main function starting server"""
        mock_process = Mock()
        
        with patch('main.check_mcp_server', return_value=False), \
             patch('main.start_mcp_server', return_value=mock_process), \
             patch('main.load_tools', return_value=[Mock()]), \
             patch('main.load_llm', return_value=Mock()), \
             patch('main.create_agent') as mock_create_agent, \
             patch('main.create_memory', return_value=Mock()), \
             patch('main.logger'), \
             patch('builtins.input', side_effect=['quit']), \
             patch('builtins.print'):
            
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value="Test response")
            mock_create_agent.return_value = mock_agent
            
            await main()
            
            # Verify server cleanup
            mock_process.terminate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_server_start_failure(self, mock_env):
        """Test main function with server start failure"""
        with patch('main.check_mcp_server', return_value=False), \
             patch('main.start_mcp_server', return_value=None), \
             patch('main.logger') as mock_logger, \
             patch('builtins.print'):
            
            await main()
            
            mock_logger.error.assert_called_with("Failed to start MCP Strava server. Exiting.")
    
    @pytest.mark.asyncio
    async def test_main_user_interaction(self, mock_env):
        """Test main function user interaction"""
        with patch('main.check_mcp_server', return_value=True), \
             patch('main.load_tools', return_value=[Mock()]), \
             patch('main.load_llm', return_value=Mock()), \
             patch('main.create_agent') as mock_create_agent, \
             patch('main.create_memory', return_value=Mock()), \
             patch('main.logger'), \
             patch('builtins.input', side_effect=['test query', 'quit']), \
             patch('builtins.print') as mock_print:
            
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value="Agent response")
            mock_create_agent.return_value = mock_agent
            
            await main()
            
            # Verify agent was called with enhanced input
            mock_agent.run.assert_called_with("[Athlete ID: 12345] test query", memory=mock_create_agent.return_value)
            mock_print.assert_any_call("Agent: Agent response")
    
    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt(self, mock_env):
        """Test main function with keyboard interrupt"""
        with patch('main.check_mcp_server', return_value=True), \
             patch('main.load_tools', side_effect=KeyboardInterrupt()), \
             patch('builtins.print') as mock_print:
            
            await main()
            
            mock_print.assert_any_call("\nReceived keyboard interrupt. Shutting down...")
    
    @pytest.mark.asyncio
    async def test_main_agent_error_handling(self, mock_env):
        """Test main function agent error handling"""
        with patch('main.check_mcp_server', return_value=True), \
             patch('main.load_tools', return_value=[Mock()]), \
             patch('main.load_llm', return_value=Mock()), \
             patch('main.create_agent') as mock_create_agent, \
             patch('main.create_memory', return_value=Mock()), \
             patch('main.logger') as mock_logger, \
             patch('builtins.input', side_effect=['test query', 'quit']), \
             patch('builtins.print') as mock_print:
            
            mock_agent = Mock()
            mock_agent.run = AsyncMock(side_effect=Exception("Agent error"))
            mock_create_agent.return_value = mock_agent
            
            await main()
            
            mock_print.assert_any_call("Error: Agent error")
            mock_logger.error.assert_called_with("Agent error: Agent error")


@pytest.mark.integration
class TestMainIntegration:
    """Integration tests for main function components"""
    
    @pytest.mark.asyncio
    async def test_full_initialization_flow(self, mock_env):
        """Test complete initialization flow"""
        with patch('main.load_dotenv') as mock_load_dotenv, \
             patch('main.check_mcp_server', return_value=True), \
             patch('main.BasicMCPClient'), \
             patch('main.McpToolSpec') as mock_mcp_tool_spec, \
             patch('main.AzureOpenAI') as mock_azure_openai, \
             patch('main.ReActAgent') as mock_react_agent, \
             patch('main.Memory') as mock_memory, \
             patch('builtins.input', side_effect=['quit']), \
             patch('builtins.print'):
            
            # Setup mocks
            mock_tool_spec = Mock()
            mock_tool_spec.to_tool_list_async = AsyncMock(return_value=[])
            mock_mcp_tool_spec.return_value = mock_tool_spec
            
            mock_llm = Mock()
            mock_azure_openai.return_value = mock_llm
            
            mock_agent = Mock()
            mock_agent.run = AsyncMock(return_value="Response")
            mock_react_agent.return_value = mock_agent
            
            mock_memory_instance = Mock()
            mock_memory.from_defaults.return_value = mock_memory_instance
            
            await main()
            
            # Verify initialization sequence
            mock_load_dotenv.assert_called_once_with('.env')
            mock_azure_openai.assert_called_once()
            mock_react_agent.assert_called_once()
            mock_memory.from_defaults.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_server_lifecycle_management(self, mock_env):
        """Test server lifecycle management"""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        
        with patch('main.check_mcp_server', return_value=False), \
             patch('main.start_mcp_server', return_value=mock_process), \
             patch('main.load_tools', return_value=[]), \
             patch('main.load_llm', return_value=Mock()), \
             patch('main.create_agent', return_value=Mock()), \
             patch('main.create_memory', return_value=Mock()), \
             patch('main.time.sleep'), \
             patch('main.logger'), \
             patch('builtins.input', side_effect=['quit']), \
             patch('builtins.print'):
            
            await main()
            
            # Verify server cleanup
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()  # Force kill after terminate