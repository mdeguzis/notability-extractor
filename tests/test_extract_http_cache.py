"""Tests for extract.http_cache against a synthesized Cache.db."""

import json
import sqlite3
from pathlib import Path

from notability_extractor.extract.http_cache import extract_learn_content


def _make_cache_db(db_path: Path) -> None:
    """Create the minimal Cache.db schema Notability uses."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE cfurl_cache_response (
            entry_ID INTEGER PRIMARY KEY,
            request_key TEXT
        );
        CREATE TABLE cfurl_cache_receiver_data (
            entry_ID INTEGER PRIMARY KEY,
            receiver_data BLOB
        );
    """)
    conn.commit()
    conn.close()


def _add_cache_row(db_path: Path, entry_id: int, url: str, uuid: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO cfurl_cache_response (entry_ID, request_key) VALUES (?, ?)",
        (entry_id, url),
    )
    conn.execute(
        "INSERT INTO cfurl_cache_receiver_data (entry_ID, receiver_data) VALUES (?, ?)",
        (entry_id, uuid.encode("utf-8")),
    )
    conn.commit()
    conn.close()


def _sample_quiz_json() -> str:
    inner = {
        "questions": [
            {
                "question": "Q1?",
                "answers": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct_answer": "B",
            }
        ]
    }
    return json.dumps({"data": {"getQuizJobContent": json.dumps(inner)}})


def test_extracts_quiz_to_quizzes_dir(tmp_path: Path):
    db = tmp_path / "Cache.db"
    fs_cache = tmp_path / "fsCachedData"
    fs_cache.mkdir()
    _make_cache_db(db)
    (fs_cache / "uuid-quiz-1").write_text(_sample_quiz_json())
    _add_cache_row(db, 1, "https://notability.com/graphql", "uuid-quiz-1")

    out = tmp_path / "learn"
    quizzes, summaries = extract_learn_content(db, fs_cache, out)
    assert quizzes == 1
    assert summaries == 0
    assert (out / "quizzes" / "quiz_1.json").is_file()
    assert (out / "quizzes" / "quiz_1.txt").is_file()


def test_extracts_summary_to_summaries_dir(tmp_path: Path):
    db = tmp_path / "Cache.db"
    fs_cache = tmp_path / "fsCachedData"
    fs_cache.mkdir()
    _make_cache_db(db)
    (fs_cache / "uuid-summary-1").write_text("# Summary\n\nBody.")
    _add_cache_row(
        db,
        2,
        "https://notability.com/learn/summary-content-stream/abc12345-job",
        "uuid-summary-1",
    )

    out = tmp_path / "learn"
    quizzes, summaries = extract_learn_content(db, fs_cache, out)
    assert quizzes == 0
    assert summaries == 1
    md_files = list((out / "summaries").glob("summary_1_*.md"))
    assert len(md_files) == 1


def test_skips_non_quiz_graphql(tmp_path: Path):
    db = tmp_path / "Cache.db"
    fs_cache = tmp_path / "fsCachedData"
    fs_cache.mkdir()
    _make_cache_db(db)
    (fs_cache / "uuid-other").write_text('{"data":{"somethingElse":true}}')
    _add_cache_row(db, 3, "https://notability.com/graphql", "uuid-other")

    out = tmp_path / "learn"
    quizzes, summaries = extract_learn_content(db, fs_cache, out)
    assert quizzes == 0
    assert summaries == 0


def test_missing_cache_db_returns_zero(tmp_path: Path):
    db = tmp_path / "nope.db"
    fs_cache = tmp_path / "fsCachedData"
    quizzes, summaries = extract_learn_content(db, fs_cache, tmp_path / "learn")
    assert (quizzes, summaries) == (0, 0)
