#!/usr/bin/env python3
"""
Memory Operations Script
========================
Provides CRUD operations for the agent memory system using SQLite.
Implements entities, observations, and relations following Anthropic's
knowledge graph memory model, plus directive execution logging.

Usage:
    python memory_ops.py init                    Initialize database
    python memory_ops.py add-entity <name> <type> [--obs "observation"]
    python memory_ops.py add-observation <entity_name> "observation text"
    python memory_ops.py add-relation <from> <to> <relation_type>
    python memory_ops.py log-run <directive> <status> [--notes "..."]
    python memory_ops.py search <query>
    python memory_ops.py get-entity <name>
    python memory_ops.py get-runs <directive> [--limit N]
    python memory_ops.py read-graph
    python memory_ops.py delete-entity <name>
    python memory_ops.py delete-observation <id>
"""

import argparse
import sqlite3
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Database path relative to this script's parent directory
DB_PATH = Path(__file__).parent.parent / "db" / "memory.db"


class MemoryDB:
    """SQLite-based knowledge graph memory system."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def init_schema(self) -> str:
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Observations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)

        # Relations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity_id INTEGER NOT NULL,
                to_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (to_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                UNIQUE(from_entity_id, to_entity_id, relation_type)
            )
        """)

        # Directive runs table (execution history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS directive_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                directive_name TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN ('started', 'success', 'failed', 'partial')),
                error_message TEXT,
                notes TEXT,
                input_summary TEXT,
                output_summary TEXT
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_directive ON directive_runs(directive_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON directive_runs(status)")

        self.conn.commit()
        return f"Database initialized at {self.db_path}"

    # --- Entity Operations ---

    def create_entity(self, name: str, entity_type: str, observations: List[str] = None) -> Dict:
        """Create a new entity with optional observations."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO entities (name, entity_type) VALUES (?, ?)",
                (name, entity_type)
            )
            entity_id = cursor.lastrowid

            if observations:
                for obs in observations:
                    cursor.execute(
                        "INSERT INTO observations (entity_id, content) VALUES (?, ?)",
                        (entity_id, obs)
                    )

            self.conn.commit()
            return {"id": entity_id, "name": name, "type": entity_type, "observations": observations or []}
        except sqlite3.IntegrityError:
            return {"error": f"Entity '{name}' already exists"}

    def get_entity(self, name: str) -> Optional[Dict]:
        """Get entity by name with all observations and relations."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM entities WHERE name = ?", (name,))
        entity = cursor.fetchone()
        if not entity:
            return None

        # Get observations
        cursor.execute(
            "SELECT id, content, created_at FROM observations WHERE entity_id = ?",
            (entity["id"],)
        )
        observations = [dict(row) for row in cursor.fetchall()]

        # Get relations (outgoing)
        cursor.execute("""
            SELECT r.id, r.relation_type, e.name as to_entity
            FROM relations r
            JOIN entities e ON r.to_entity_id = e.id
            WHERE r.from_entity_id = ?
        """, (entity["id"],))
        relations_out = [dict(row) for row in cursor.fetchall()]

        # Get relations (incoming)
        cursor.execute("""
            SELECT r.id, r.relation_type, e.name as from_entity
            FROM relations r
            JOIN entities e ON r.from_entity_id = e.id
            WHERE r.to_entity_id = ?
        """, (entity["id"],))
        relations_in = [dict(row) for row in cursor.fetchall()]

        return {
            "id": entity["id"],
            "name": entity["name"],
            "type": entity["entity_type"],
            "created_at": entity["created_at"],
            "observations": observations,
            "relations_outgoing": relations_out,
            "relations_incoming": relations_in
        }

    def delete_entity(self, name: str) -> Dict:
        """Delete entity and cascade to observations/relations."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM entities WHERE name = ?", (name,))
        self.conn.commit()
        if cursor.rowcount > 0:
            return {"deleted": name}
        return {"error": f"Entity '{name}' not found"}

    # --- Observation Operations ---

    def add_observation(self, entity_name: str, content: str) -> Dict:
        """Add observation to existing entity."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM entities WHERE name = ?", (entity_name,))
        entity = cursor.fetchone()
        if not entity:
            return {"error": f"Entity '{entity_name}' not found"}

        cursor.execute(
            "INSERT INTO observations (entity_id, content) VALUES (?, ?)",
            (entity["id"], content)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "entity": entity_name, "content": content}

    def delete_observation(self, obs_id: int) -> Dict:
        """Delete observation by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM observations WHERE id = ?", (obs_id,))
        self.conn.commit()
        if cursor.rowcount > 0:
            return {"deleted_observation_id": obs_id}
        return {"error": f"Observation {obs_id} not found"}

    # --- Relation Operations ---

    def create_relation(self, from_name: str, to_name: str, relation_type: str) -> Dict:
        """Create relation between two entities."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT id FROM entities WHERE name = ?", (from_name,))
        from_entity = cursor.fetchone()
        if not from_entity:
            return {"error": f"Entity '{from_name}' not found"}

        cursor.execute("SELECT id FROM entities WHERE name = ?", (to_name,))
        to_entity = cursor.fetchone()
        if not to_entity:
            return {"error": f"Entity '{to_name}' not found"}

        try:
            cursor.execute(
                "INSERT INTO relations (from_entity_id, to_entity_id, relation_type) VALUES (?, ?, ?)",
                (from_entity["id"], to_entity["id"], relation_type)
            )
            self.conn.commit()
            return {"from": from_name, "to": to_name, "relation": relation_type}
        except sqlite3.IntegrityError:
            return {"error": "Relation already exists"}

    # --- Directive Run Operations ---

    def log_run_start(self, directive: str, input_summary: str = None) -> int:
        """Log the start of a directive run."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO directive_runs (directive_name, status, input_summary) VALUES (?, 'started', ?)",
            (directive, input_summary)
        )
        self.conn.commit()
        return cursor.lastrowid

    def log_run_end(self, run_id: int, status: str, notes: str = None,
                    error_message: str = None, output_summary: str = None) -> Dict:
        """Update a directive run with completion status."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE directive_runs
            SET ended_at = CURRENT_TIMESTAMP, status = ?, notes = ?,
                error_message = ?, output_summary = ?
            WHERE id = ?
        """, (status, notes, error_message, output_summary, run_id))
        self.conn.commit()
        return {"run_id": run_id, "status": status}

    def log_run(self, directive: str, status: str, notes: str = None,
                error_message: str = None, input_summary: str = None,
                output_summary: str = None) -> Dict:
        """Log a complete directive run (for quick logging after the fact)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO directive_runs
            (directive_name, ended_at, status, notes, error_message, input_summary, output_summary)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
        """, (directive, status, notes, error_message, input_summary, output_summary))
        self.conn.commit()
        return {"run_id": cursor.lastrowid, "directive": directive, "status": status}

    def get_runs(self, directive: str = None, limit: int = 10, status: str = None) -> List[Dict]:
        """Get recent directive runs, optionally filtered."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM directive_runs WHERE 1=1"
        params = []

        if directive:
            query += " AND directive_name = ?"
            params.append(directive)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # --- Search & Graph Operations ---

    def search(self, query: str) -> Dict:
        """Search across entity names, types, and observations."""
        cursor = self.conn.cursor()
        pattern = f"%{query}%"

        # Search entities
        cursor.execute("""
            SELECT DISTINCT e.* FROM entities e
            WHERE e.name LIKE ? OR e.entity_type LIKE ?
        """, (pattern, pattern))
        entities = [dict(row) for row in cursor.fetchall()]

        # Search observations
        cursor.execute("""
            SELECT o.*, e.name as entity_name FROM observations o
            JOIN entities e ON o.entity_id = e.id
            WHERE o.content LIKE ?
        """, (pattern,))
        observations = [dict(row) for row in cursor.fetchall()]

        # Search directive runs
        cursor.execute("""
            SELECT * FROM directive_runs
            WHERE directive_name LIKE ? OR notes LIKE ? OR error_message LIKE ?
            ORDER BY started_at DESC LIMIT 20
        """, (pattern, pattern, pattern))
        runs = [dict(row) for row in cursor.fetchall()]

        return {"entities": entities, "observations": observations, "directive_runs": runs}

    def read_graph(self) -> Dict:
        """Read entire knowledge graph."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM entities ORDER BY created_at DESC")
        entities = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT r.*, e1.name as from_name, e2.name as to_name
            FROM relations r
            JOIN entities e1 ON r.from_entity_id = e1.id
            JOIN entities e2 ON r.to_entity_id = e2.id
        """)
        relations = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) as count FROM observations")
        obs_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM directive_runs")
        runs_count = cursor.fetchone()["count"]

        return {
            "entities": entities,
            "relations": relations,
            "stats": {
                "entity_count": len(entities),
                "relation_count": len(relations),
                "observation_count": obs_count,
                "directive_runs_count": runs_count
            }
        }


def main():
    parser = argparse.ArgumentParser(
        description="Agent Memory System - SQLite knowledge graph operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python memory_ops.py init
  python memory_ops.py add-entity "user" "person" --obs "Prefers concise responses"
  python memory_ops.py add-observation "user" "Works on data projects"
  python memory_ops.py add-relation "user" "project_x" "owns"
  python memory_ops.py log-run "scrape_website" "success" --notes "Scraped 50 pages"
  python memory_ops.py search "scrape"
  python memory_ops.py get-runs "scrape_website" --limit 5
  python memory_ops.py read-graph
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    subparsers.add_parser("init", help="Initialize the database schema")

    # add-entity
    p = subparsers.add_parser("add-entity", help="Create a new entity")
    p.add_argument("name", help="Unique entity name")
    p.add_argument("type", help="Entity type (person, project, api, tool, etc.)")
    p.add_argument("--obs", action="append", help="Initial observations (can repeat)")

    # add-observation
    p = subparsers.add_parser("add-observation", help="Add observation to entity")
    p.add_argument("entity", help="Entity name")
    p.add_argument("content", help="Observation text")

    # add-relation
    p = subparsers.add_parser("add-relation", help="Create relation between entities")
    p.add_argument("from_entity", help="Source entity name")
    p.add_argument("to_entity", help="Target entity name")
    p.add_argument("relation_type", help="Relation type (uses, owns, depends_on, etc.)")

    # log-run
    p = subparsers.add_parser("log-run", help="Log a directive execution")
    p.add_argument("directive", help="Directive name (e.g., scrape_website)")
    p.add_argument("status", choices=["started", "success", "failed", "partial"])
    p.add_argument("--notes", help="Execution notes/observations")
    p.add_argument("--error", help="Error message if failed")
    p.add_argument("--input", help="Input summary")
    p.add_argument("--output", help="Output summary")

    # search
    p = subparsers.add_parser("search", help="Search across all memory")
    p.add_argument("query", help="Search query")

    # get-entity
    p = subparsers.add_parser("get-entity", help="Get entity details")
    p.add_argument("name", help="Entity name")

    # get-runs
    p = subparsers.add_parser("get-runs", help="Get directive run history")
    p.add_argument("directive", nargs="?", help="Filter by directive name")
    p.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    p.add_argument("--status", choices=["started", "success", "failed", "partial"])

    # read-graph
    subparsers.add_parser("read-graph", help="Read entire knowledge graph")

    # delete-entity
    p = subparsers.add_parser("delete-entity", help="Delete entity (cascades)")
    p.add_argument("name", help="Entity name")

    # delete-observation
    p = subparsers.add_parser("delete-observation", help="Delete observation by ID")
    p.add_argument("id", type=int, help="Observation ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    db = MemoryDB()

    try:
        if args.command == "init":
            result = db.init_schema()
        elif args.command == "add-entity":
            result = db.create_entity(args.name, args.type, args.obs)
        elif args.command == "add-observation":
            result = db.add_observation(args.entity, args.content)
        elif args.command == "add-relation":
            result = db.create_relation(args.from_entity, args.to_entity, args.relation_type)
        elif args.command == "log-run":
            result = db.log_run(
                args.directive, args.status,
                notes=args.notes, error_message=args.error,
                input_summary=args.input, output_summary=args.output
            )
        elif args.command == "search":
            result = db.search(args.query)
        elif args.command == "get-entity":
            result = db.get_entity(args.name)
            if not result:
                result = {"error": f"Entity '{args.name}' not found"}
        elif args.command == "get-runs":
            result = db.get_runs(args.directive, args.limit, args.status)
        elif args.command == "read-graph":
            result = db.read_graph()
        elif args.command == "delete-entity":
            result = db.delete_entity(args.name)
        elif args.command == "delete-observation":
            result = db.delete_observation(args.id)
        else:
            result = {"error": f"Unknown command: {args.command}"}

        print(json.dumps(result, indent=2, default=str))

    finally:
        db.close()


if __name__ == "__main__":
    main()
