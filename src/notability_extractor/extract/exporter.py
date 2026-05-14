"""Phase 1 orchestrator: walk notes, walk HTTP cache, write export dir."""

from pathlib import Path

from notability_extractor.extract.http_cache import extract_learn_content
from notability_extractor.extract.nbn import extract_nbn
from notability_extractor.utils import get_logger

log = get_logger(__name__)


def run_extract(notes_dir: Path, cache_dir: Path, output_dir: Path) -> None:
    """Walk a notes directory and an HTTP cache, populate output_dir.

    notes_dir   - parent of *.nbn bundles (typically iCloud Drive location)
    cache_dir   - parent of Cache.db and fsCachedData/ (sandbox container)
    output_dir  - where to write the extracted data
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_pdfs_dir = output_dir / "raw_pdfs"
    raw_pdfs_dir.mkdir(exist_ok=True)

    note_count = 0
    if notes_dir.is_dir():
        for bundle in sorted(notes_dir.glob("*.nbn")):
            if not bundle.is_dir():
                continue
            out_text = output_dir / f"{bundle.stem}.txt"
            extract_nbn(bundle, out_text, raw_pdfs_dir)
            note_count += 1
    else:
        log.warning("Notes dir not found: %s", notes_dir)

    learn_out = output_dir / "learn"
    cache_db = cache_dir / "Cache.db"
    fs_cache = cache_dir / "fsCachedData"
    quiz_count, summary_count = extract_learn_content(cache_db, fs_cache, learn_out)

    log.info(
        "Phase 1 complete: %d notes, %d quizzes, %d summaries -> %s",
        note_count,
        quiz_count,
        summary_count,
        output_dir,
    )
