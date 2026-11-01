# 10Q1P - Multi-Agent Suite via Model Context Protocol (MCP)

A modular **Hierarchical Multi-Agent Architecture** connecting humans to an autonomous **Main Orchestrator (Hermes Agent / Host)**, which delegates to specialized **Domain Sub-Agents**, **Worker Agents**, and **Deterministic Tools** via MCP.

---

## The 5-Layer Architecture

```
👤 HUMAN (Telegram / Discord / Terminal / Web)
   │
   ▼
👑 MAIN AGENT (Hermes Agent / Orchestrator)
   │
   ├── [MCP Protocol via stdio / SSE]
   │
   ▼
📂 DOMAIN SUB-AGENTS (subagents/database, subagents/ingestion, etc.)
   │
   ▼
👷 SPECIALIST WORKER AGENTS (workers/ddl_worker.py, query_worker.py)
   │
   ▼
🛠️ CONCRETE TOOLS (schema_tools.py, execution_tools.py)
```

---

## Directory Organization

```
10Q1P/
├── subagents/
│   ├── database/                     # 🗄️ Database Domain Sub-Agent
│   │   ├── subagent.py               # Coordinates DB workers & tools
│   │   │
│   │   ├── workers/                  # 👷 Specialist Worker Agents
│   │   │   ├── ddl_worker.py         # Gemini DDL Agent (dry-run & self-healing)
│   │   │   └── __init__.py
│   │   │
│   │   ├── tools/                    # 🛠️ Concrete DB Primitives
│   │   │   ├── db_connection.py      # PostgreSQL / Neon SSL connection
│   │   │   ├── schema_tools.py       # inspect_table, list_tables
│   │   │   ├── execution_tools.py    # dry_run, execute_committed, read_query
│   │   │   └── __init__.py
│   │   │
│   │   ├── models/                   # Pydantic Schemas
│   │   │   ├── schemas.py            # DDLTaskInput, DDLTaskOutput, TableStatus
│   │   │   └── __init__.py
│   │   │
│   │   └── __init__.py               # MCP Registration Hook
│   │
│   └── ingestion/                    # 📁 (Future) File Ingestion Sub-Agent
│
├── server.py                         # 🔌 Master MCP Server (Mounts sub-agents)
├── main.py                           # 💻 CLI Interface for direct manual testing
├── example_parent_agent.py           # 🧪 Simulation of Main Agent calling Database Sub-Agent
├── test_agent.py                     # ✅ Unit Test Suite
├── requirements.txt
└── .env
```

---

## Registered MCP Tools

When `server.py` runs, it exposes:

1. **`postgres_manage_table_ddl`** *(Agentic Worker Tool)*:
   - Full autonomous DDL workflow: pre-flight schema inspection $\rightarrow$ Gemini SQL generation $\rightarrow$ dry-run validation $\rightarrow$ committed execution.
2. **`postgres_list_tables`** *(Deterministic Tool)*:
   - Direct query of all tables in a schema.
3. **`postgres_inspect_table`** *(Deterministic Tool)*:
   - Returns column definitions, nullability, defaults, primary keys, and indexes.
4. **`postgres_read_query`** *(Deterministic Tool)*:
   - Safe read-only `SELECT` query runner.

---

## How to Run

### 1. Run as an MCP Server (For Hermes / Claude / Main Agent):
```powershell
.\.venv\Scripts\python.exe server.py
```

### 2. Run Manually via CLI:
```powershell
.\.venv\Scripts\python.exe main.py
```

### 3. Run Simulated Main Agent Call:
```powershell
.\.venv\Scripts\python.exe example_parent_agent.py
```

### 4. Run Unit Tests:
```powershell
.\.venv\Scripts\python.exe test_agent.py
```
