# notability-extractor

Extract flashcards from Notability's local SQLite database and export them as an Anki `.apkg` deck.

## Requirements

- Python 3.11+
- No third-party packages required (stdlib only)

## Where is the database? (macOS)

Notability stores its data in one of these locations:

```
~/Library/Group Containers/com.gingerlabs.Notability/
~/Library/Containers/com.gingerlabs.Notability/Data/Library/Application Support/
```

The script auto-discovers any `.sqlite` file under these directories. If your Mac has
iCloud sync enabled, these files are present even if the iPad is the primary device.

**iPadOS note:** The sandbox prevents direct access without a jailbreak. Use macOS.

## Usage

First install so the `notability-extractor` console script lands on PATH:

```bash
make install
```

Then:

```bash
# Auto-discover DB and export
notability-extractor

# Specify DB explicitly
notability-extractor --db ~/Library/Group\ Containers/com.gingerlabs.Notability/Notability.sqlite

# Inspect tables first (useful when DB schema is unknown)
notability-extractor --list-tables

# Target a specific table and custom output path
notability-extractor --table ZFLASHCARD --out my_deck.apkg --deck-name "Biology 101"
```

## Caveats: BLOBs and Protobufs

Notability sometimes stores flashcard text as binary BLOBs or Protocol Buffers rather
than plain text columns. The extractor will flag these columns in the log output:

```
WARNING: Column ZDATA contains non-UTF-8 binary data -- likely protobuf or nbn blob
```

If you hit this, the `.nbn` note files (stored alongside the `.sqlite`) are the next
place to look. They are renamed `.zip` archives containing binary metadata. A future
version of this tool may add protobuf decoding support.

## Importing into Anki

1. Open Anki on your desktop.
2. `File > Import` and select the generated `.apkg` file.
3. The deck will appear as "Notability Flashcards" (or whatever you passed to `--deck-name`).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No DB found | Not on macOS, or iCloud hasn't synced | Pass `--db` explicitly |
| No flashcard tables | Different Notability version | Use `--list-tables` to inspect |
| All backs are empty | Content in BLOB columns | Check WARNING logs; protobuf decode needed |
| Import error in Anki | Anki version mismatch | Open a GitHub issue with your Anki version |
