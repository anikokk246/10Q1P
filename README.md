# 10Q1P - PostgreSQL DDL AI Agent (Python)

An intelligent agent that connects to PostgreSQL (including Neon with SSL), inspects the target database schema, generates verified DDL via Google Gemini, runs a dry-run safety validation, executes the DDL in a transaction, and returns structured before-and-after feedback.

---

## Architecture & Workflow

```
1. Receive Input (DB URL, Schema, Table, Instructions)
         │
         ▼
2. Pre-flight DB Check (information_schema)
   ├── Exists? NO  ──► Generate CREATE TABLE
   └── Exists? YES ──► Introspect Columns ──► Generate ALTER TABLE
         │
         ▼
3. Dry-Run Validation (BEGIN; <SQL>; ROLLBACK;)
   └── (Auto-correction retry loop if SQL errors occur)
         │
         ▼
4. Committed Transaction Execution (BEGIN; <SQL>; COMMIT;)
         │
         ▼
5. Output Schema Diff & Detailed Feedback Report
```

---

## Setup

1. **Create and activate the virtual environment:**
   ```powershell
   .\.venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Create a `.env` file based on `.env.example`:
   ```ini
   DATABASE_URL=postgresql://neondb_owner:npg_xxxx@ep-cool-sample.us-east-2.aws.neon.tech/neondb?sslmode=require
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

---

## Usage

### Interactive Mode:
```powershell
.\.venv\Scripts\python.exe main.py
```
You will be prompted for:
- Schema name (e.g. `public`)
- Table name (e.g. `users`)
- Table instructions (e.g. `id uuid primary key, email text unique not null, status text default 'active'`)

### Command-Line Arguments Mode:
```powershell
.\.venv\Scripts\python.exe main.py \
  --schema public \
  --table orders \
  --instructions "id uuid primary key, user_id uuid references users(id), amount numeric(10,2) not null, created_at timestamptz default now(), index on user_id"
```

### Run Tests:
```powershell
.\.venv\Scripts\python.exe test_agent.py
```
