"""Initialise la base SQLite et les agents Govern IA."""

import sqlite3

from database import DB_PATH, create_database


AGENTS = (
    ("QualityAgent", "quality"),
    ("ClassificationAgent", "classification"),
    ("SecurityAgent", "security"),
    ("LineageAgent", "lineage"),
    ("DocumentationAgent", "documentation"),
)


def initialize_agents():
    """Ajoute les cinq agents, sans creer de doublons si relance."""
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executemany(
            """
            INSERT OR IGNORE INTO agents (name, agent_type, status)
            VALUES (?, ?, 'active')
            """,
            AGENTS,
        )
        connection.commit()
    finally:
        connection.close()


def main():
    create_database()
    initialize_agents()
    print(f"Base SQLite initialisee : {DB_PATH}")


if __name__ == "__main__":
    main()