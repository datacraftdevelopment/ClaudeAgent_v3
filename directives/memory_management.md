# Memory Management Directive

> Standard operating procedure for using the agent memory system.

## Purpose

The memory system provides persistent context across sessions. It tracks:
- **Entities**: People, projects, APIs, tools, concepts
- **Observations**: Facts and learnings about entities
- **Relations**: How entities connect to each other
- **Directive runs**: History of what directives were executed and outcomes

## When to Use Memory

### Read Memory (Before Work)

**MUST** check memory before executing any directive:

```bash
# Check for relevant past runs
python3 execution/memory_ops.py get-runs "<directive_name>" --limit 5

# Search for related context
python3 execution/memory_ops.py search "<relevant_keywords>"
```

Use this to understand:
- What happened last time this directive ran
- Any errors or edge cases encountered
- Lessons learned that affect current execution

### Write Memory (After Work)

**MUST** log every directive run:

```bash
# Success
python3 execution/memory_ops.py log-run "<directive_name>" "success" \
  --notes "Completed in X minutes. Processed N items." \
  --input "Brief input summary" \
  --output "Brief output summary"

# Failure
python3 execution/memory_ops.py log-run "<directive_name>" "failed" \
  --error "Error message" \
  --notes "Root cause and what to try next time"

# Partial success
python3 execution/memory_ops.py log-run "<directive_name>" "partial" \
  --notes "Completed X of Y. Stopped due to..."
```

### Create Entities (When Learning)

When you discover important context that should persist:

```bash
# New API with quirks
python3 execution/memory_ops.py add-entity "openai_api" "api" \
  --obs "Rate limit is 60 requests/minute" \
  --obs "Batch endpoint available at /v1/batch"

# New person/contact
python3 execution/memory_ops.py add-entity "john_client" "person" \
  --obs "Prefers weekly updates via email"

# New project
python3 execution/memory_ops.py add-entity "project_alpha" "project" \
  --obs "Uses Python 3.11" \
  --obs "Deployed on AWS Lambda"
```

### Add Observations (Ongoing Learning)

When you learn something new about an existing entity:

```bash
python3 execution/memory_ops.py add-observation "openai_api" \
  "GPT-4 turbo has 128k context window"
```

### Create Relations (Connecting Knowledge)

When entities are connected:

```bash
python3 execution/memory_ops.py add-relation "project_alpha" "openai_api" "uses"
python3 execution/memory_ops.py add-relation "john_client" "project_alpha" "owns"
```

## Memory Query Patterns

### Before Running a Directive

```bash
# What happened recently with this directive?
python3 execution/memory_ops.py get-runs "scrape_website" --limit 3

# Any failed runs to learn from?
python3 execution/memory_ops.py get-runs "scrape_website" --status failed --limit 5
```

### Searching for Context

```bash
# Find anything related to a topic
python3 execution/memory_ops.py search "rate limit"

# Get full details on an entity
python3 execution/memory_ops.py get-entity "openai_api"
```

### Understanding the Full Graph

```bash
# See everything in memory
python3 execution/memory_ops.py read-graph
```

## Status Definitions

| Status | Meaning |
|--------|---------|
| `started` | Directive execution began (use for long-running tasks) |
| `success` | Completed without errors |
| `failed` | Did not complete, error occurred |
| `partial` | Partially completed, stopped early |

## Best Practices

1. **Be specific in notes**: Include numbers, timings, and specific outcomes
2. **Log failures with root causes**: Future runs will benefit from knowing why something failed
3. **Create entities for recurring topics**: If you mention something 3+ times, it deserves an entity
4. **Keep observations atomic**: One fact per observation, easy to add/remove
5. **Use active voice for relations**: "uses", "owns", "depends_on" not "is used by"

## Example Workflow

```
Before:
  → Check: python3 execution/memory_ops.py get-runs "pdf_to_markdown"
  → Found: Last run failed due to OCR timeout on large PDFs
  → Adjust: Will process in smaller batches

Execute:
  → Run the directive with adjusted approach

After:
  → Log: python3 execution/memory_ops.py log-run "pdf_to_markdown" "success" \
         --notes "Batched into 10-page chunks. Total time: 5 min for 50 pages."
  → Learn: python3 execution/memory_ops.py add-observation "pdf_processing" \
           "Batch size of 10 pages avoids OCR timeout"
```
