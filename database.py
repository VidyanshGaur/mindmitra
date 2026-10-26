"""SQLite persistence layer for the MindMitra demo application."""

from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).parent / "mindmitra.db"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database() -> None:
    """Create the application's local storage tables when needed."""
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                reminder_time TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS mood_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at TEXT NOT NULL,
                mood TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS game_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game TEXT NOT NULL,
                score INTEGER NOT NULL,
                out_of INTEGER NOT NULL,
                played_at TEXT NOT NULL
            );
            """
        )


def load_reminders() -> list[dict]:
    with _connection() as connection:
        rows = connection.execute("SELECT id, task, reminder_time, done FROM reminders ORDER BY id DESC").fetchall()
    return [{"id": row["id"], "task": row["task"], "when": row["reminder_time"], "done": bool(row["done"])} for row in rows]


def add_reminder(task: str, when: str) -> dict:
    with _connection() as connection:
        cursor = connection.execute("INSERT INTO reminders (task, reminder_time) VALUES (?, ?)", (task, when))
        reminder_id = cursor.lastrowid
    return {"id": reminder_id, "task": task, "when": when, "done": False}


def update_reminder_status(reminder_id: int, done: bool) -> None:
    with _connection() as connection:
        connection.execute("UPDATE reminders SET done = ? WHERE id = ?", (int(done), reminder_id))


def load_moods() -> list[dict]:
    with _connection() as connection:
        rows = connection.execute("SELECT id, logged_at, mood FROM mood_logs ORDER BY id DESC").fetchall()
    return [{"id": row["id"], "date": row["logged_at"], "mood": row["mood"]} for row in rows]


def add_mood(logged_at: str, mood: str) -> dict:
    with _connection() as connection:
        cursor = connection.execute("INSERT INTO mood_logs (logged_at, mood) VALUES (?, ?)", (logged_at, mood))
        mood_id = cursor.lastrowid
    return {"id": mood_id, "date": logged_at, "mood": mood}


def load_scores() -> list[dict]:
    with _connection() as connection:
        rows = connection.execute("SELECT id, game, score, out_of, played_at FROM game_scores ORDER BY id DESC").fetchall()
    return [dict(row) | {"date": row["played_at"]} for row in rows]


def add_score(game: str, score: int, out_of: int, played_at: str) -> dict:
    with _connection() as connection:
        cursor = connection.execute(
            "INSERT INTO game_scores (game, score, out_of, played_at) VALUES (?, ?, ?, ?)",
            (game, score, out_of, played_at),
        )
        score_id = cursor.lastrowid
    return {"id": score_id, "game": game, "score": score, "out_of": out_of, "date": played_at}
