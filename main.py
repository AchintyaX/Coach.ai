from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent import ReActAgent
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.openai import OpenAI
from llama_index.core.memory import Memory
from llama_index.core import PromptTemplate, Settings
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from dotenv import load_dotenv
import os
import asyncio
import subprocess
import time
import requests
import logging
import sys
from loguru import logger
from prompts import FITNESS_COACH_SYSTEM_PROMPT

def setup_enhanced_logging():
    """
    Setup enhanced logging and debugging for LlamaIndex agents.
    
    This configures:
    1. LlamaIndex debug handler for detailed tool calling and LLM traces
    2. Enhanced logging with different colors for user input vs agent output
    3. Callback manager for monitoring agent execution
    """
    # Set up LlamaIndex debugging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))
    
    # Create LlamaDebugHandler for detailed agent tracing
    llama_debug = LlamaDebugHandler(print_trace_on_end=True)
    callback_manager = CallbackManager([llama_debug])
    
    # Configure global Settings with callback manager
    Settings.callback_manager = callback_manager
    
    # Configure loguru for different log levels and colors
    logger.remove()  # Remove default handler
    
    # Add colored handlers for different types of output
    logger.add(
        sys.stdout,
        format="<green>[{time:HH:mm:ss}]</green> <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        filter=lambda record: record["level"].name in ["INFO", "SUCCESS"]
    )
    
    logger.add(
        sys.stdout,
        format="<yellow>[{time:HH:mm:ss}]</yellow> <level>{level: <8}</level> | <magenta>{name}</magenta>:<magenta>{function}</magenta>:<magenta>{line}</magenta> - <level>{message}</level>",
        level="DEBUG",
        filter=lambda record: record["level"].name == "DEBUG"
    )
    
    logger.add(
        sys.stdout,
        format="<red>[{time:HH:mm:ss}]</red> <level>{level: <8}</level> | <red>{name}</red>:<red>{function}</red>:<red>{line}</red> - <level>{message}</level>",
        level="WARNING"
    )
    
    # Set LlamaIndex to use verbose logging
    import llama_index.core
    llama_index.core.set_global_handler("simple")
    
    logger.info("🔧 Enhanced logging and debugging enabled")
    logger.info("📊 LlamaDebugHandler configured for detailed agent traces")
    logger.info("🎨 Color-coded logging setup complete")
    
    return callback_manager

def print_user_input(message: str):
    """Print user input with distinctive formatting"""
    print(f"\n{'='*60}")
    print(f"🧑 USER INPUT: {message}")
    print(f"{'='*60}")

def print_agent_output(message: str):
    """Print agent output with distinctive formatting"""
    print(f"\n{'*'*60}")
    print(f"🤖 AGENT RESPONSE:")
    print(f"{'*'*60}")
    print(f"{message}")
    print(f"{'*'*60}\n")

async def load_tools():
    # Load MCP tools (Strava)
    strava_mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    strava_mcp_tool = McpToolSpec(client=strava_mcp_client)
    strava_tools = await strava_mcp_tool.to_tool_list_async()
    
    # Load Tavily MCP tools (Search)
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    tavily_mcp_client = BasicMCPClient(f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}")
    tavily_mcp_tool = McpToolSpec(client=tavily_mcp_client)
    tavily_tools = await tavily_mcp_tool.to_tool_list_async()
    
    # Load Workout Database MCP tools (STDIO)
    workout_mcp_client = BasicMCPClient("python", args=["workout_db_server.py"])
    workout_mcp_tool = McpToolSpec(client=workout_mcp_client)
    workout_tools = await workout_mcp_tool.to_tool_list_async()
    
    # Combine all tools
    all_tools = strava_tools + tavily_tools + workout_tools
    
    # Log all tools with categories
    logger.info("=== LOADED MCP TOOLS ===")
    logger.info(f"Strava Tools ({len(strava_tools)}):")
    for tool in strava_tools:
        logger.info(f"  - {tool.metadata.name}: {tool.metadata.description}")
    
    logger.info(f"\nTavily Search Tools ({len(tavily_tools)}):")
    for tool in tavily_tools:
        logger.info(f"  - {tool.metadata.name}: {tool.metadata.description}")
    
    logger.info(f"\nWorkout Database Tools ({len(workout_tools)}):")
    for tool in workout_tools:
        logger.info(f"  - {tool.metadata.name}: {tool.metadata.description}")
    
    logger.info(f"\nTotal Tools Loaded: {len(all_tools)}")
    
    return all_tools

def load_llm():
    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if llm_provider == "openai":
        return OpenAI(
            model="gpt-5-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.0
        )
    elif llm_provider == "azure":
        return AzureOpenAI(
            model=os.getenv("AZURE_MODEL_NAME"),
            deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
            api_key=os.getenv("AZURE_API_KEY"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version=os.getenv("AZURE_API_VERSION"),
            temperature=0.0
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}. Supported providers: 'azure', 'openai'")

def create_agent(tools, llm, callback_manager):
    """
    Create a ReActAgent with enhanced debugging and logging capabilities.
    
    Args:
        tools: List of tools for the agent
        llm: Language model instance
        callback_manager: Callback manager for debugging
    
    Returns:
        Configured ReActAgent with verbose logging and debugging
    """
    agent = ReActAgent(
        tools=tools,
        llm=llm,
        verbose=True,  # Enable verbose mode for detailed output
        callback_manager=callback_manager  # Add callback manager for debugging
    )
    
    # Create custom fitness coach system prompt
    fitness_coach_prompt = PromptTemplate(FITNESS_COACH_SYSTEM_PROMPT)
    
    # Update the agent with our custom system prompt using the correct key
    agent.update_prompts({"react_header": fitness_coach_prompt})
    
    logger.info("🤖 ReActAgent created with verbose logging enabled")
    logger.info(f"🛠️  Agent configured with {len(tools)} tools")
    
    return agent

def create_memory():
    """Create memory for context retention"""
    return Memory.from_defaults(
        session_id="fitness_coach_session",
        token_limit=40000
    )

def check_mcp_server():
    """Check if MCP Strava server is running on SSE endpoint"""
    try:
        # Try to connect to the SSE endpoint
        response = requests.get("http://127.0.0.1:8000/sse", timeout=5, stream=True)
        # For SSE endpoints, we expect a successful connection (200) or SSE-specific responses
        return response.status_code in [200, 204] or 'text/event-stream' in response.headers.get('content-type', '')
    except (requests.RequestException, requests.ConnectionError):
        return False

def start_mcp_server():
    """Start the MCP Strava server using uv run python strava_server.py"""
    try:
        logger.info("Starting MCP Strava server...")
        process = subprocess.Popen(
            ["uv", "run", "python", "strava_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a bit for the server to start
        time.sleep(3)
        
        # Check if server is now running
        max_retries = 10
        for _ in range(max_retries):
            if check_mcp_server():
                logger.info("MCP Strava server started successfully")
                return process
            time.sleep(1)
        
        logger.error("Failed to start MCP Strava server after waiting")
        return None
        
    except Exception as e:
        logger.error(f"Error starting MCP Strava server: {e}")
        return None

async def main():
    load_dotenv('.env')  # Load environment variables from .env file
    
    # Setup enhanced logging and debugging first
    callback_manager = setup_enhanced_logging()
    
    server_process = None
    server_started_by_us = False
    
    # Check if MCP Strava server is running, start if not
    if not check_mcp_server():
        logger.info("MCP Strava server not running, starting it...")
        server_process = start_mcp_server()
        server_started_by_us = True
        if not server_process:
            logger.error("Failed to start MCP Strava server. Exiting.")
            return
    else:
        logger.info("MCP Strava server is already running")
    
    try:
        logger.info("🚀 Loading MCP tools and initializing agent...")
        tools = await load_tools()
        llm = load_llm()
        agent = create_agent(tools, llm, callback_manager)
        
        # Load athlete ID from environment
        athlete_id = os.getenv('STRAVA_CLIENT_ID', 'Unknown')
        
        # Create memory for conversation retention
        memory = create_memory()
        
        # Interactive chat loop with enhanced formatting
        print(f"\n🏃 FITNESS COACH REACTAGENT IS READY!")
        print(f"👤 Working with Athlete ID: {athlete_id}")
        print(f"🔧 Available tools: Strava data, web search, and comprehensive workout database management")
        print(f"🔍 Enhanced debugging: Tool calls, LLM traces, and agent reasoning will be shown")
        print(f"💬 Type 'quit' to exit. The agent will remember our conversation across messages.")
        print(f"📋 Try asking: 'Create a user profile for me' or 'Add a workout to my plan'")
        print(f"{'='*80}")
        
        while True:
            user_input = input("\n🧑 You: ")
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            try:
                # Print formatted user input
                print_user_input(user_input)
                
                # Add athlete context to the user input
                enhanced_input = f"[Athlete ID: {athlete_id}] {user_input}"
                
                logger.debug(f"Processing user input: {user_input}")
                logger.debug(f"Enhanced input with context: {enhanced_input}")
                
                # Run agent with memory and capture response
                response = await agent.run(enhanced_input, memory=memory)
                
                # Print formatted agent output
                print_agent_output(str(response))
                
                logger.success("Agent response completed successfully")
                
            except Exception as e:
                logger.error(f"Agent execution error: {e}")
                print(f"\n❌ Error: {e}")
                
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...")
        logger.warning("Application interrupted by user")
    
    finally:
        # Clean up: kill the server if we started it
        if server_started_by_us and server_process:
            logger.info("Shutting down MCP Strava server...")
            try:
                server_process.terminate()
                # Wait a bit for graceful shutdown
                time.sleep(2)
                # Force kill if still running
                if server_process.poll() is None:
                    server_process.kill()
                logger.info("MCP Strava server stopped")
            except Exception as e:
                logger.error(f"Error stopping MCP Strava server: {e}")
        
        logger.info("👋 Goodbye!")
        print("👋 Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())