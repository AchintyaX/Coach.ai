from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.tools.duckduckgo import DuckDuckGoSearchToolSpec
from llama_index.core.agent import ReActAgent
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.memory import Memory
from llama_index.core import PromptTemplate
from dotenv import load_dotenv
import os
import asyncio
import subprocess
import time
import requests
from loguru import logger
from prompts import FITNESS_COACH_SYSTEM_PROMPT

async def load_tools():
    # Load MCP tools (Strava)
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)
    mcp_tools = await mcp_tool.to_tool_list_async()
    
    # Load DuckDuckGo search tools
    ddg_tool = DuckDuckGoSearchToolSpec()
    ddg_tools = ddg_tool.to_tool_list()
    
    # Combine all tools
    all_tools = mcp_tools + ddg_tools
    
    # Log all tools
    for tool in all_tools:
        logger.info(f"Tool Name - {tool.metadata.name}\n Tool Description - {tool.metadata.description}")
    
    return all_tools

def load_llm():
    return AzureOpenAI(
        model=os.getenv("AZURE_MODEL_NAME"),
        deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_API_KEY"),
        azure_endpoint=os.getenv("AZURE_ENDPOINT"),
        api_version=os.getenv("AZURE_API_VERSION"),
        temperature=0.0
    )

def create_agent(tools, llm):
    agent = ReActAgent(
        tools=tools,
        llm=llm,
        verbose=True
    )
    
    # Create custom fitness coach system prompt
    fitness_coach_prompt = PromptTemplate(FITNESS_COACH_SYSTEM_PROMPT)
    
    # Update the agent with our custom system prompt using the correct key
    #agent.update_prompts({"react_header": fitness_coach_prompt})
    
    return agent

def create_memory():
    """Create memory for context retention"""
    return Memory.from_defaults(
        session_id="strava_coach_session",
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
        for i in range(max_retries):
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
        tools = await load_tools()
        llm = load_llm()
        agent = create_agent(tools, llm)
        
        # Load athlete ID from environment
        athlete_id = os.getenv('STRAVA_CLIENT_ID', 'Unknown')
        
        # Create memory for conversation retention
        memory = create_memory()
        
        # Interactive chat loop
        print(f"ReActAgent with memory is ready! Working with Athlete ID: {athlete_id}")
        print("Type 'quit' to exit. The agent will remember our conversation across messages.")
        
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            try:
                # Add athlete context to the user input
                enhanced_input = f"[Athlete ID: {athlete_id}] {user_input}"
                response = await agent.run(enhanced_input, memory=memory)
                print(f"Agent: {response}")
            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"Agent error: {e}")
                
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...")
    
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
        
        print("Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())