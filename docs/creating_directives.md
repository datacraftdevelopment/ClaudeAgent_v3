# Creating New Directives

You don't write directives manually. You have a conversation with Claude Code and let it build everything for you.

## The Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Start conversation                                      │
│     "I want to automate X..."                               │
├─────────────────────────────────────────────────────────────┤
│  2. Provide context                                         │
│     - Paste examples, files, screenshots                    │
│     - Share what you've done before                         │
│     - Explain edge cases you know about                     │
├─────────────────────────────────────────────────────────────┤
│  3. Claude creates a plan                                   │
│     - What the directive should cover                       │
│     - What execution scripts are needed                     │
│     - How the pieces fit together                           │
├─────────────────────────────────────────────────────────────┤
│  4. Claude builds it                                        │
│     - Writes the directive to directives/                   │
│     - Creates execution scripts in execution/               │
│     - Tests that scripts work                               │
├─────────────────────────────────────────────────────────────┤
│  5. You run it                                              │
│     - Claude follows the directive                          │
│     - Logs results to memory                                │
│     - Improves directive based on what happens              │
└─────────────────────────────────────────────────────────────┘
```

## Example Conversation

### You:
> I want to scrape product data from e-commerce sites. Here's an example of the output format I need [pastes CSV]. I've done this manually before using BeautifulSoup. The tricky part is pagination — some sites use "Load More" buttons instead of page links.

### Claude:
> Got it. Let me create a directive and execution script for this. I'll handle both pagination styles...
>
> *Creates `directives/scrape_products.md`*
> *Creates `execution/product_scraper.py`*
> *Tests the script*
>
> Here's what I built. The directive covers the goal, inputs, execution steps, and edge cases for both pagination types. Want me to run it on a test URL?

### You:
> Yeah, try it on [URL]

### Claude:
> *Runs the directive*
> *Logs result to memory*
>
> Worked. Got 47 products. I hit a rate limit after 30 requests so I added a 2-second delay. I've updated the directive with that edge case and logged it to memory.

## What You Provide

The more context, the better the directive:

| Context Type | Example |
|--------------|---------|
| **Goal** | "I want to convert PDFs to markdown for RAG" |
| **Examples** | Paste sample inputs/outputs |
| **Past work** | "I've done this before using PyMuPDF" |
| **Edge cases** | "Some PDFs are scanned images, need OCR" |
| **Constraints** | "Must run in under 5 minutes" |
| **Preferences** | "Output to Google Sheets, not local files" |

### The `context/` Folder

Drop reference materials into `context/` before starting a conversation:

```
context/
├── sample_input.pdf          # Example of what you'll process
├── expected_output.md        # What the result should look like
├── api_docs.md               # Relevant API documentation
└── previous_attempt.py       # Code you've tried before
```

Then tell Claude:
> "Check the context folder. I've added samples of the input format and what I want the output to look like."

Claude will read these files and use them to build a better directive. This is faster than pasting everything into the chat.

## What Claude Creates

### Directive (`directives/*.md`)

A structured SOP with:
- **Goal**: What this accomplishes
- **Inputs**: What's needed to run it
- **Execution**: Step-by-step with script calls
- **Outputs**: What gets produced
- **Edge cases**: Known issues and how to handle them

### Execution Scripts (`execution/*.py`)

Deterministic Python that:
- Has clear `--help` documentation
- Handles errors gracefully
- Returns structured output
- Can be tested independently

## Iteration

After the first run, you refine through conversation:

> "That worked but it was slow. Can we parallelize it?"

> "The output format is wrong. Here's what I actually need..."

> "We need to handle this new edge case I just discovered..."

Claude updates the directive and scripts based on feedback.

## Tips

### Be Specific About Outputs
Instead of "scrape the data", say "scrape product name, price, and URL into a CSV with these column headers".

### Share Failures
If you've tried this before and it failed, share what went wrong. Claude will design around those issues.

### Start Small
Get one simple case working, then expand. "Start with a single page, we'll add pagination later."

### Let Claude Test
Don't skip the testing step. Let Claude run the script and hit real errors — that's how the directive gets hardened.

## Memory Integration

When creating new directives, Claude should:

1. **Check memory first**: Are there related directives or past learnings?
   ```bash
   python3 execution/memory_ops.py search "scraping"
   ```

2. **Create entities**: If this directive involves new APIs, tools, or concepts:
   ```bash
   python3 execution/memory_ops.py add-entity "ecommerce_scraper" "tool" \
     --obs "Handles pagination" \
     --obs "2-second delay to avoid rate limits"
   ```

3. **Log the creation**: Track that a new directive was built:
   ```bash
   python3 execution/memory_ops.py log-run "create_directive" "success" \
     --notes "Created scrape_products directive with pagination support"
   ```

## The Point

You're not writing code or documentation. You're having a conversation about what you want, providing context, and letting Claude build the system. The directive becomes a reusable artifact that Claude (or any LLM) can follow reliably in the future.

This is the actual workflow — conversational development, not manual authoring.
