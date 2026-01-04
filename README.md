# Claude Agent v3

A template for building reliable AI agents with persistent memory. Designed for Claude Code, but works with any LLM that can execute Python scripts.

## The Problem

LLMs are probabilistic. Business logic is deterministic. When you ask an AI to do multi-step tasks, errors compound:

> 90% accuracy per step = 59% success over 5 steps

This agent architecture fixes that mismatch by separating concerns and adding memory.

## The Solution

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Directives                                │
│  └── What to do (Markdown SOPs in directives/)     │
├─────────────────────────────────────────────────────┤
│  Layer 2: Orchestration                             │
│  └── Decision making (Claude reads CLAUDE.md)      │
├─────────────────────────────────────────────────────┤
│  Layer 3: Execution                                 │
│  └── Doing the work (Python scripts in execution/) │
├─────────────────────────────────────────────────────┤
│  Memory Layer                                       │
│  └── Persistent context (SQLite in memory.db)      │
└─────────────────────────────────────────────────────┘
```

**Directives** are SOPs written in Markdown — clear instructions like you'd give a mid-level employee.

**Orchestration** is the AI's job — read directives, call scripts, handle errors, make decisions.

**Execution** is deterministic Python — API calls, data processing, file operations. Reliable and testable.

**Memory** persists across sessions — what happened, what was learned, what to do differently next time.

## Project Structure

```
ClaudeAgent_v3/
├── CLAUDE.md                 # Agent instructions (start here)
├── memory.db                 # SQLite knowledge graph
├── execution/
│   └── memory_ops.py         # Memory CRUD operations
├── directives/
│   └── memory_management.md  # How to use memory
├── docs/
│   └── memory_setup.md       # Technical documentation
└── .tmp/                     # Temporary files (gitignored)
```

## Quick Start

### 1. Clone and Initialize

```bash
git clone https://github.com/datacraftdevelopment/ClaudeAgent_v3.git
cd ClaudeAgent_v3

# Database is already initialized, but you can reset with:
python3 execution/memory_ops.py init
```

### 2. Open with Claude Code

```bash
claude
```

Claude will automatically read `CLAUDE.md` and understand the architecture.

### 3. Create Directives Through Conversation

You don't write directives manually. You have a conversation with Claude about what you want:

```
You:    "I want to scrape product data from e-commerce sites.
         Here's an example of the output format I need..."

Claude: Creates directives/scrape_products.md
        Creates execution/product_scraper.py
        Tests that it works

You:    "Try it on this URL"

Claude: Runs the directive
        Logs results to memory
        Updates directive with edge cases discovered
```

**What you provide:**
- Your goal ("I want to automate X...")
- Context (paste examples, files, past work)
- Edge cases you know about
- Preferences for output format

**What Claude creates:**
- Directive in `directives/` (the SOP)
- Execution scripts in `execution/` (the tools)
- Memory entries for learnings

See **[docs/creating_directives.md](docs/creating_directives.md)** for the full workflow.

## Memory System

The memory system follows [Anthropic's knowledge graph model](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) but uses local SQLite instead of MCP.

### Core Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| **Entities** | Nodes in the graph | `openai_api` (type: api) |
| **Observations** | Facts about entities | "Rate limit is 60/min" |
| **Relations** | Connections between entities | `project → uses → api` |
| **Directive Runs** | Execution history | What happened, errors, learnings |

### Usage

```bash
# Before running a directive — check what happened last time
python3 execution/memory_ops.py get-runs "scrape_website" --limit 5

# After running — log the outcome
python3 execution/memory_ops.py log-run "scrape_website" "success" \
  --notes "Scraped 50 products. Rate limit hit at page 3, backed off."

# Create entities for things you'll reference again
python3 execution/memory_ops.py add-entity "target_api" "api" \
  --obs "Rate limit 100/hour" \
  --obs "Returns JSON"

# Add learnings over time
python3 execution/memory_ops.py add-observation "target_api" \
  "Batch endpoint available at /v2/bulk"

# Connect related things
python3 execution/memory_ops.py add-relation "my_project" "target_api" "uses"

# Search across all memory
python3 execution/memory_ops.py search "rate limit"

# View the full knowledge graph
python3 execution/memory_ops.py read-graph
```

### Why This Matters

Without memory, Claude starts fresh every session. With memory:

- **Before**: "Last time I ran this, I hit a rate limit at 50 requests. I'll batch in groups of 40."
- **After**: "Completed successfully with batch size 40. Logging this for next time."

The agent genuinely learns from experience.

## Self-Annealing

When something breaks, the system gets stronger:

1. **Error occurs** → Log it with details
2. **Fix applied** → Update the script
3. **Test passes** → Verify the fix
4. **Directive updated** → Add the edge case
5. **Memory updated** → Create observations for the pattern

Next time, the agent knows to avoid that failure mode.

## Adding to Your Project

### Option 1: Use as Template

Fork this repo and add your own directives and execution scripts.

### Option 2: Copy the Memory System

Just take `execution/memory_ops.py` and add it to any existing project. Initialize with:

```bash
python3 execution/memory_ops.py init
```

### Option 3: Adapt the Architecture

Use the 3-layer pattern (directives → orchestration → execution) with whatever memory system fits your needs.

## Configuration

### Environment Variables

Create a `.env` file for API keys and configuration:

```bash
OPENAI_API_KEY=sk-...
DATABASE_URL=...
```

### Memory Location

By default, `memory.db` lives in the project root. The database is portable — copy the folder and memory comes with it.

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — Agent instructions (what Claude reads)
- **[docs/creating_directives.md](docs/creating_directives.md)** — How to create new directives through conversation
- **[docs/memory_setup.md](docs/memory_setup.md)** — Technical details on the memory system
- **[directives/memory_management.md](directives/memory_management.md)** — SOP for using memory

## Why Not MCP?

Anthropic's [MCP memory server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) is great for global Claude Desktop memory. This approach is better when you want:

- **Project-specific memory** — Different contexts for different projects
- **Portability** — Memory travels with the folder
- **No external dependencies** — Just Python + SQLite
- **Inspectable** — Query with standard SQL tools
- **Fits the execution layer** — It's just another Python script

## License

MIT — Use it however you want.
