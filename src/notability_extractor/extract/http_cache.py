"""Parse Notability's HTTP cache (Cache.db + fsCachedData) for AI Learn content."""

import json
import sqlite3
from pathlib import Path

from notability_extractor.utils import get_logger

log = get_logger(__name__)


def extract_learn_content(
    cache_db: Path,
    fs_cache: Path,
    out_dir: Path,
) -> tuple[int, int]:
    """Extract cached quizzes and summaries. Returns (quiz_count, summary_count)."""
    if not cache_db.is_file():
        log.warning("No HTTP cache DB found at %s", cache_db)
        return 0, 0

    quizzes_dir = out_dir / "quizzes"
    summaries_dir = out_dir / "summaries"
    quizzes_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)

    rows = _query_cache_db(cache_db)
    quiz_count = 0
    summary_count = 0
    for uuid, url in rows:
        if not uuid:
            continue
        src = fs_cache / uuid
        if not src.is_file():
            continue
        if "/graphql" in url:
            if _try_save_quiz(src, quizzes_dir, quiz_count + 1):
                quiz_count += 1
        elif "/learn/summary-content-stream/" in url:
            _save_summary(src, url, summaries_dir, summary_count + 1)
            summary_count += 1

    return quiz_count, summary_count


def _query_cache_db(cache_db: Path) -> list[tuple[str, str]]:
    conn = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    rows = conn.execute("""
        SELECT CAST(d.receiver_data AS TEXT), r.request_key
        FROM cfurl_cache_receiver_data d
        JOIN cfurl_cache_response r ON d.entry_ID = r.entry_ID
        WHERE r.request_key LIKE '%notability.com%'
        """).fetchall()
    conn.close()
    return rows


def _try_save_quiz(src: Path, quizzes_dir: Path, n: int) -> bool:
    content = src.read_text(errors="replace")
    if "getQuizJobContent" not in content:
        return False
    (quizzes_dir / f"quiz_{n}.json").write_text(content)
    _write_quiz_text(content, quizzes_dir / f"quiz_{n}.txt")
    log.info("Extracted quiz_%d.json", n)
    return True


def _save_summary(src: Path, url: str, summaries_dir: Path, n: int) -> None:
    job_id = url.rsplit("/", 1)[-1]
    short = job_id[:8]
    target = summaries_dir / f"summary_{n}_{short}.md"
    target.write_text(src.read_text(errors="replace"))
    log.info("Extracted summary_%d_%s.md", n, short)


def _write_quiz_text(quiz_json: str, out: Path) -> None:
    """Render the double-encoded quiz JSON as human-readable Q&A."""
    outer = json.loads(quiz_json)
    inner = json.loads(outer["data"]["getQuizJobContent"])
    lines: list[str] = []
    for i, q in enumerate(inner["questions"], 1):
        lines.append(f"Q{i}. {q['question']}")
        for letter in ("A", "B", "C", "D"):
            lines.append(f"  {letter}) {q['answers'].get(letter, '')}")
        lines.append(f"  -> Correct: {q['correct_answer']}")
        lines.append("")
    out.write_text("\n".join(lines))
