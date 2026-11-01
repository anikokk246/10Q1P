"""
server.py - Master MCP Server

Connects the Main Agent (Hermes Agent / Claude / Orchestrator) to our fleet of
Domain Sub-Agents, Worker Agents, and Deterministic Tools via Model Context Protocol.
"""

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from subagents.database import register_database_mcp

load_dotenv()

# Initialize Master MCPServer
server = MCPServer("Multi-Agent-Suite")

# Mount Database Sub-Agent (Worker Agents & Tools)
register_database_mcp(server)

# Future Sub-Agents can be mounted with 1 line:
# from subagents.ingestion import register_ingestion_mcp
# register_ingestion_mcp(server)

if __name__ == "__main__":
    server.run()
