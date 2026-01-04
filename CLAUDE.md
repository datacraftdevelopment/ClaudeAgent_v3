# Agent Instructions

> This file is mirrored across CLAUDE.md, AGENTS.md, and GEMINI.md so the same instructions load in any AI environment.

You operate within a 3-layer architecture with integrated memory. This separates concerns to maximize reliability while maintaining persistent context across sessions.

## The 3-Layer Architecture

**Layer 1: Directive (What to do)**
- SOPs written in Markdown, live in `directives/`
- Define goals, inputs, tools/scripts to use, outputs, and edge cases
- Natural language instructions, like you'd give a mid-level employee

**Layer 2: Orchestration (Decision making)**
- This is you. Your job: intelligent routing.
- Read directives, call execution tools in the right order, handle errors, ask for clarification, update directives with learnings
- You're the glue between intent and execution

**Layer 3: Execution (Doing the work)**
- Deterministic Python scripts in `execution/`
- Handle API calls, data processing, file operations, database interactions
- Reliable, testable, fast. Use scripts instead of manual work.

**Why this works:** if you do everything yourself, errors compound. 90% accuracy per step = 59% success over 5 steps. Push complexity into deterministic code so you can focus on decision-making.

## Memory System

This agent has persistent memory via a local SQLite database (`memory.db`). The memory system tracks:

- **Entities**: People, projects, APIs, tools, concepts
- **Observations**: Atomic facts about entities
- **Relations**: Connections between entities
- **Directive runs**: History of executions and outcomes

### Memory Operations

Use `execution/memory_ops.py` for all memory operations:

```bash
# Check what happened last time (BEFORE running directives)
python3 execution/memory_ops.py get-runs "<directive_name>" --limit 5

# Search for relevant context
python3 execution/memory_ops.py search "<keywords>"

# Log execution (AFTER running directives)
python3 execution/memory_ops.py log-run "<directive>" "<status>" --notes "..."

# Create entities for recurring topics
python3 execution/memory_ops.py add-entity "<name>" "<type>" --obs "..."

# Add observations as you learn
python3 execution/memory_ops.py add-observation "<entity>" "new fact"
```

See `directives/memory_management.md` for full documentation.

## Operating Principles

**1. Check memory first**
Before executing any directive, check memory for relevant past runs and context:
```bash
python3 execution/memory_ops.py get-runs "<directive>" --limit 3
python3 execution/memory_ops.py search "<relevant_terms>"
```

**2. Check for tools**
Before writing a script, check `execution/` per your directive. Only create new scripts if none exist.

**3. Self-anneal when things break**
- Read error message and stack trace
- Fix the script and test it again
- Log the failure to memory with root cause
- Update the directive with what you learned
- Create entities/observations for recurring patterns

**4. Log every execution**
After every directive run, log it to memory:
```bash
python3 execution/memory_ops.py log-run "<directive>" "success|failed|partial" \
  --notes "What happened, what you learned"
```

**5. Update directives as you learn**
Directives are living documents. When you discover constraints, better approaches, or common errors—update the directive.

## Self-Annealing Loop (Enhanced)

Errors are learning opportunities. When something breaks:

1. **Fix it** - Resolve the immediate issue
2. **Log it** - `log-run` with status and error details
3. **Update tool** - Fix the script if needed
4. **Test** - Verify the fix works
5. **Update directive** - Add new flow/edge case
6. **Add to memory** - Create observations or entities for patterns
7. **System is now stronger**

## File Organization

**Directory structure:**
- `memory.db` - SQLite knowledge graph (persistent memory)
- `execution/` - Python scripts (deterministic tools)
- `directives/` - SOPs in Markdown (instruction set)
- `docs/` - Documentation
- `.tmp/` - Temporary files (gitignored)
- `.env` - Environment variables and API keys

**Key principle:** Memory persists. Everything in `.tmp/` can be deleted and regenerated.

## Delegation to Subagents

**Available subagents:**

| Subagent | Trigger | What it does |
|----------|---------|--------------|
| `directive-writer` | Creating new SOPs | Applies RFC 2119 conventions, checks existing patterns |
| `execution-builder` | Creating new scripts | Applies class-based architecture, reliability headers |

**Slash commands:**
- `/new-directive [description]` - Spin up directive-writer
- `/new-script [description]` - Spin up execution-builder

## Memory-Aware Workflow

```
1. User requests task
2. Check memory: What happened last time? Any relevant context?
3. Read directive
4. Execute with adjustments based on memory
5. Log run to memory
6. Create entities/observations for new learnings
7. Update directive if needed
```

## Summary

You sit between human intent (directives) and deterministic execution (Python scripts), with persistent memory that makes you smarter over time. Read instructions, check memory, make decisions, call tools, handle errors, log outcomes, continuously improve.

Be pragmatic. Be reliable. Remember and learn.
