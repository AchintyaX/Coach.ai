from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent import ReActAgentWorker, StructuredPlannerAgent
from llama_index.llms.openai import OpenAI
from prompts import INITIAL_PLAN_PROMPT, PLAN_REFINE_PROMPT
from dotenv import load_dotenv
import os
from loguru import logger

def load_tools():
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)
    tools = mcp_tool.to_tool_list()
    for tool in tools:
        logger.info(f"Tool Name - {tool.metadata.name}\n Tool Description - { tool.metadata.description}")
    return tools

def load_llm():
    return OpenAI(model="gpt-4o", temperature=0.0)

def create_agent(tools, llm):
    worker = ReActAgentWorker(
        tools=tools,
        llm=llm,
        verbose=True
    )
    return StructuredPlannerAgent(
        tools=tools,
        llm=llm,
        verbose=True,
        initial_plan_prompt=INITIAL_PLAN_PROMPT,
        plan_refine_prompt=PLAN_REFINE_PROMPT,
        agent_worker=worker,
    )

if __name__ == "__main__":
    load_dotenv('.env')  # Load environment variables from .env file
    tools = load_tools()
    llm = load_llm()
    agent = create_agent(tools, llm)
    agent.chat_repl()