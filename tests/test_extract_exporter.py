"""End-to-end test for the extract orchestrator."""

import plistlib
import sqlite3
import zipfile
from pathlib import Path

from notability_extractor.extract.exporter import run_extract


def test_orchestrates_notes_and_learn(tmp_path: Path):
    # synthesize one .nbn bundle
    notes_dir = tmp_path / "Documents"
    notes_dir.mkdir()
    bundle = notes_dir / "Note1.nbn"
    bundle.mkdir()
    hw = bundle / "HandwritingIndex"
    hw.mkdir()
    with (hw / "index.plist").open("wb") as f:
        plistlib.dump({"pages": [{"text": "hand-written content"}]}, f)
    pdf_idx = bundle / "NBPDFIndex"
    pdf_idx.mkdir()
    with zipfile.ZipFile(pdf_idx / "PDFIndex.zip", "w") as zf:
        zf.writestr("X.pdf/PDFTextIndex.txt", "pdf body text")

    # synthesize Cache.db with one quiz
    cache_dir = tmp_path / "Caches"
    cache_dir.mkdir()
    fs_cache = cache_dir / "fsCachedData"
    fs_cache.mkdir()
    quiz = (
        '{"data":{"getQuizJobContent":"'
        '{\\"questions\\":[{\\"question\\":\\"Q?\\",\\"answers\\":'
        '{\\"A\\":\\"a\\",\\"B\\":\\"b\\",\\"C\\":\\"c\\",\\"D\\":\\"d\\"},'
        '\\"correct_answer\\":\\"B\\"}]}"}}'
    )
    (fs_cache / "qq").write_text(quiz)
    db = cache_dir / "Cache.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE cfurl_cache_response (entry_ID INTEGER PRIMARY KEY, request_key TEXT);
        CREATE TABLE cfurl_cache_receiver_data (entry_ID INTEGER PRIMARY KEY, receiver_data BLOB);
    """)
    conn.execute(
        "INSERT INTO cfurl_cache_response VALUES (1, ?)",
        ("https://notability.com/graphql",),
    )
    conn.execute("INSERT INTO cfurl_cache_receiver_data VALUES (1, ?)", (b"qq",))
    conn.commit()
    conn.close()

    out = tmp_path / "export"
    run_extract(notes_dir, cache_dir, out)

    assert (out / "Note1.txt").is_file()
    assert (out / "learn" / "quizzes" / "quiz_1.json").is_file()
    assert "hand-written content" in (out / "Note1.txt").read_text()
