# notability-extractor

Extract Notability Learn content (AI-generated quizzes, summaries, and OCR'd
note text) and export it as an Anki `.apkg` deck, JSON, or Markdown for review.

## How it works

Notability Learn generates quizzes via Claude Haiku and summaries via Gemini
2.5 Flash, server-side. Both get cached locally in the app's HTTP cache.
Handwriting OCR and PDF text live inside `.nbn` note bundles.

The tool runs in two phases:

1. **Extract** (macOS only): walks the iCloud Drive `.nbn` bundles and the
   HTTP cache (`Cache.db` + `fsCachedData/`), writes a normalized export
   directory at `~/notability_export/`.
2. **Build** (any OS): reads the export directory, merges flashcards into a
   persistent JSONL archive at `~/.notability_extractor/cards.jsonl`, and
   emits outputs: `.apkg` for Anki, `.json` for programmatic review, `.md`
   for human reading.

Linux and Windows machines can skip phase 1 by pointing `--input-dir` at a
directory produced on a Mac. Useful if you want to do the Anki packaging on a
different machine than the one Notability runs on.

The JSONL archive is the source of truth for flashcards. Both the CLI and the
GUI read from and write to it, and the build always reconstructs `.apkg` from
the archive (not the input dir) so edits and tags persist across rebuilds.

## Install

From PyPI:

```bash
pip install notability-extractor
# or with uv:
uv tool install notability-extractor
```

From source (for development):

```bash
git clone https://github.com/mdeguzis/notability-extractor.git
cd notability-extractor
make install
```

`make install` sets up `.venv/` for dev work and drops the
`notability-extractor` console script into `~/.local/bin/` so it's runnable
from any shell.

## Usage

```bash
# macOS: auto-extract and build all outputs in the current dir
notability-extractor

# Anywhere: build from a pre-extracted directory
notability-extractor --input-dir ~/notability_export

# Custom output directory
notability-extractor --input-dir ~/notability_export --out-dir ./decks

# macOS: just run phase 1 (produce export dir, no .apkg/json/md)
notability-extractor --extract-only

# Custom Anki deck name (only affects what shows up inside Anki)
notability-extractor --deck-name "Biology 101"
```

Output filenames are fixed:

| File | Contents |
|---|---|
| `notability_flashcards.apkg` | Anki deck (quiz questions only) |
| `notability_flashcards.json` | Full structured dump for programmatic review |
| `notability_flashcards.md` | Human-readable flashcards |
| `notability_notes.{json,md}` | Note transcripts |
| `notability_summaries.{json,md}` | Generated summaries |

### Archive management CLI flags

```bash
# Open a prompt-driven editor against the archive
notability-extractor --edit-flashcards

# One-shot interactive add
notability-extractor --add-card

# Print archive contents (optionally filter by tag)
notability-extractor --list-cards
notability-extractor --list-cards --tag biology

# Backup / restore round-trip
notability-extractor --backup
notability-extractor --export ~/cards-backup.jsonl
notability-extractor --import ~/cards-backup.jsonl --mode merge
notability-extractor --import ~/cards-backup.jsonl --mode replace

# Launch the GUI
notability-extractor --gui
```

## GUI

A PySide6 desktop companion ships in the same package. After install:

```bash
notability-extractor-gui
```

Pages: Library (browse / edit / add / delete cards with tag filter), Notes
(read-only), Summaries (read-only), Build (export apkg / json / md), Settings
(theme, paths, backups, schedule).

On Wayland with no `DISPLAY` set, the GUI auto-applies
`QT_QPA_PLATFORM=wayland` so SSH/login sessions don't need a manual export.

## Backups

The archive at `~/.notability_extractor/cards.jsonl` is snapshotted on every
save to `~/.notability_extractor/backups/cards-YYYYMMDD-HHMMSS.jsonl`,
hash-deduped so unchanged saves don't make redundant copies. Default retention
is the last 10 snapshots (configurable in Settings).

For a scheduled backup when the GUI is closed, run from cron:

```
0 * * * * notability-extractor --backup
```

The Settings page surfaces this exact line for convenience.

## Importing into Anki

1. Open Anki on your desktop.
2. `File > Import` and select the generated `.apkg` file.
3. The deck appears as "Notability Flashcards" (or whatever you passed to
   `--deck-name`).

## Caveats

- The Learn cache only contains content from sessions you've actively opened
  in Notability. If a note has never had Learn run on it, no quiz is cached.
- Notability does not provide a stable export API. The tool reads on-disk
  formats that could change between app versions. If extraction breaks after
  a Notability update, open an issue.
- iPadOS-only setups need iCloud Drive sync enabled so the `.nbn` bundles and
  cache files are present on a Mac. Without sync, you'd need physical access
  to the iPad's sandbox (not currently supported).

## Releasing

Releases are automated via GitHub Actions. To cut a new release:

1. Bump the `version = "X.Y.Z"` line in `pyproject.toml`
2. Commit and push to `main`
3. CI runs: tests pass -> autotag creates `vX.Y.Z` -> build produces wheel
   and sdist -> GitHub Release is created -> PyPI publishes via OIDC
   trusted publishing

No manual tag step. No API tokens in CI.

### One-time PyPI setup

(Skip this if the package is already on PyPI with OIDC configured.)

1. First upload manually with `./upload-to-pypi.sh` (needs `~/.pypirc` with
   a PyPI API token) to claim the package name.
2. On PyPI: project settings -> Publishing -> add trusted publisher with
   repo `mdeguzis/notability-extractor`, workflow `ci.yml`, environment
   `pypi`.
3. On GitHub: repo settings -> Environments -> create `pypi` environment.

### Manual ad-hoc upload

Only needed if CI is broken:

```bash
./upload-to-pypi.sh --test   # TestPyPI dry-run first
./upload-to-pypi.sh          # then prod PyPI
```
