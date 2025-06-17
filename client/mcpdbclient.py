# Use server from examples/servers/streamable-http-stateless/

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_core.messages import HumanMessage, ToolMessage , AIMessage

from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools

import argparse
import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from langchain_openai import OpenAI

import getpass
import os

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

class MCPClient:
    """MCP Client for interacting with an MCP Streamable HTTP server"""
    
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()  

    async def connect_to_streamable_http_server(
    self, server_url: str, headers: Optional[dict] = None
    ):
        """Connect to an MCP server running with HTTP Streamable transport"""
        self._streams_context = streamablehttp_client(  # pylint: disable=W0201
            url=server_url,
            headers=headers or {},
        )
        read_stream, write_stream, _ = await self._streams_context.__aenter__()  # pylint: disable=E1101

        self._session_context = ClientSession(read_stream, write_stream)  # pylint: disable=W0201
        self.session: ClientSession = await self._session_context.__aenter__()  # pylint: disable=C2801

        await self.session.initialize()

async def call_agent(inputs, agent):
        async for s in agent.astream(inputs, stream_mode="values"):
            for message in s["messages"]:
                if isinstance(message, ToolMessage):
                    print(f"\n🔧 Tool called: {message.name}")
                    print(f"📤 Tool input: {message.tool_call_id}")
                    print(f"📥 Tool response: {message.content}")  # or print the full message
                elif isinstance(message, AIMessage) and message.additional_kwargs.get("function_call"):
                    print(f"Tool called in LLM output: {message.additional_kwargs['function_call'].get('name')}")

async def main():
    """Main function to run the MCP client"""
    parser = argparse.ArgumentParser(description="Run MCP Streamable http based Client")
    parser.add_argument(
        "--mcp-localhost-port", type=int, default=8123, help="Localhost port to bind to"
    )
    args = parser.parse_args()

    client = MCPClient()

    session = await client.connect_to_streamable_http_server(
        f"http://localhost:3000/mcp"
    )
    
    # Get tools
    tools = await load_mcp_tools(client.session)
    agent = create_react_agent("openai:gpt-4.1", tools)
    query ='''can you give me order details for john.doe@example.com'''    
    inputs = {"messages": [HumanMessage(content=query)]}
    await call_agent(inputs,agent)

    query ='''please change the order date for id 2 to April 8 2027'''    
    inputs = {"messages": [HumanMessage(content=query)]}
    await call_agent(inputs,agent)

    query ='''list all pending orders'''    
    inputs = {"messages": [HumanMessage(content=query)]}
    await call_agent(inputs,agent)


    print(f"Tools Exited")

if __name__ == "__main__":
    asyncio.run(main())       
