# Memory System Setup

This document explains the agent memory system architecture and setup.

## Overview

The memory system provides persistent context for Claude agents using a local SQLite database. It follows Anthropic's knowledge graph model with three core concepts:

- **Entities**: Nodes representing people, projects, APIs, tools, concepts
- **Observations**: Atomic facts attached to entities
- **Relations**: Directed connections between entities

Additionally, it includes **directive run logging** to track execution history.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Agent Architecture                     │
├─────────────────────────────────────────────────────────┤
│  CLAUDE.md          │  Agent instructions + memory ops  │
│  directives/*.md    │  Task-specific SOPs                │
│  execution/*.py     │  Deterministic Python scripts      │
│  memory.db          │  SQLite knowledge graph            │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

### Tables

#### `entities`
Primary nodes in the knowledge graph.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Unique identifier |
| entity_type | TEXT | Category (person, project, api, tool, etc.) |
| created_at | TIMESTAMP | Creation time |

#### `observations`
Atomic facts attached to entities.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| entity_id | INTEGER | Foreign key to entities |
| content | TEXT | The observation text |
| created_at | TIMESTAMP | Creation time |

#### `relations`
Directed connections between entities.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| from_entity_id | INTEGER | Source entity |
| to_entity_id | INTEGER | Target entity |
| relation_type | TEXT | Relationship type (uses, owns, depends_on) |
| created_at | TIMESTAMP | Creation time |

#### `directive_runs`
Execution history for directives.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| directive_name | TEXT | Name of the directive |
| started_at | TIMESTAMP | When execution started |
| ended_at | TIMESTAMP | When execution ended |
| status | TEXT | started, success, failed, partial |
| error_message | TEXT | Error details if failed |
| notes | TEXT | Observations about the run |
| input_summary | TEXT | What was the input |
| output_summary | TEXT | What was produced |

## File Structure

```
project/
├── CLAUDE.md              # Agent instructions (loads memory ops)
├── memory.db              # SQLite database (auto-created)
├── execution/
│   └── memory_ops.py      # Memory CRUD operations
├── directives/
│   └── memory_management.md  # How to use memory
├── docs/
│   └── memory_setup.md    # This file
└── .tmp/                  # Temporary files (gitignored)
```

## Usage

### Initialization

The database is auto-created when you first run any command:

```bash
python3 execution/memory_ops.py init
```

### Available Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize database schema |
| `add-entity` | Create new entity |
| `add-observation` | Add fact to entity |
| `add-relation` | Connect two entities |
| `log-run` | Record directive execution |
| `search` | Search across all memory |
| `get-entity` | Get entity with observations/relations |
| `get-runs` | Get directive run history |
| `read-graph` | Dump entire knowledge graph |
| `delete-entity` | Remove entity (cascades) |
| `delete-observation` | Remove specific observation |

### Examples

```bash
# Create an entity with observations
python3 execution/memory_ops.py add-entity "openai_api" "api" \
  --obs "Rate limit 60/min" \
  --obs "Supports streaming"

# Add more observations later
python3 execution/memory_ops.py add-observation "openai_api" \
  "Batch API available for async processing"

# Create relationships
python3 execution/memory_ops.py add-entity "pdf_converter" "project"
python3 execution/memory_ops.py add-relation "pdf_converter" "openai_api" "uses"

# Log a directive run
python3 execution/memory_ops.py log-run "convert_pdfs" "success" \
  --notes "Processed 10 files in 2 minutes" \
  --input "10 PDF files from /input" \
  --output "10 markdown files to /output"

# Search memory
python3 execution/memory_ops.py search "rate limit"

# Check past runs before executing
python3 execution/memory_ops.py get-runs "convert_pdfs" --limit 5

# View entire graph
python3 execution/memory_ops.py read-graph
```

## Design Decisions

### Why SQLite (not MCP)?

1. **No external dependencies**: Works anywhere Python runs
2. **Project-specific**: Memory stays with the project folder
3. **Portable**: Just copy the folder, memory comes with it
4. **Inspectable**: Standard SQL tools can query it
5. **Fits the execution layer**: It's just another Python script

### Why JSONL for MCP but SQLite here?

MCP's knowledge graph uses JSONL for simplicity and streaming. We use SQLite because:
- Better query performance as memory grows
- Proper indexing for search operations
- ACID compliance for reliability
- Native support for relations via foreign keys

### Entity Types (Suggested)

| Type | Use For |
|------|---------|
| person | Users, clients, team members |
| project | Codebases, initiatives |
| api | External services, endpoints |
| tool | Scripts, utilities |
| concept | Patterns, approaches, learnings |
| file | Important files referenced often |
| error | Recurring error patterns |

### Relation Types (Suggested)

| Type | Example |
|------|---------|
| uses | project → api |
| owns | person → project |
| depends_on | tool → api |
| related_to | concept → concept |
| caused_by | error → tool |
| resolved_by | error → concept |

## Maintenance

### Viewing Raw Data

```bash
sqlite3 memory.db ".schema"
sqlite3 memory.db "SELECT * FROM entities"
sqlite3 memory.db "SELECT * FROM directive_runs ORDER BY started_at DESC LIMIT 10"
```

### Backup

```bash
cp memory.db memory.db.backup
```

### Reset

```bash
rm memory.db
python3 execution/memory_ops.py init
```

## Integration with Self-Annealing

The memory system enhances the self-annealing loop:

1. **Error occurs** → Log run as failed with error details
2. **Fix applied** → Add observation about what fixed it
3. **Pattern emerges** → Create entity for the error pattern
4. **Next run** → Check memory, avoid known issues

This creates a system that genuinely learns from experience.
