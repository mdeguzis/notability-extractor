"""Tests for extract.nbn against synthetic .nbn bundles."""

import plistlib
import zipfile
from pathlib import Path

from notability_extractor.extract.nbn import extract_nbn


def _make_nbn(
    path: Path,
    hw_pages: list[str],
    pdf_texts: dict[str, str],
    pdfs: list[str],
) -> Path:
    """Build a synthetic .nbn directory bundle. Returns the bundle path."""
    bundle = path / "TestNote.nbn"
    bundle.mkdir()
    # HandwritingIndex/index.plist
    hw_dir = bundle / "HandwritingIndex"
    hw_dir.mkdir()
    plist_data = {"pages": [{"text": t} for t in hw_pages]}
    with (hw_dir / "index.plist").open("wb") as f:
        plistlib.dump(plist_data, f)
    # NBPDFIndex/PDFIndex.zip
    pdf_dir = bundle / "NBPDFIndex"
    pdf_dir.mkdir()
    with zipfile.ZipFile(pdf_dir / "PDFIndex.zip", "w") as zf:
        for uuid, text in pdf_texts.items():
            zf.writestr(f"{uuid}.pdf/PDFTextIndex.txt", text)
    # Raw PDFs at the bundle root
    for name in pdfs:
        (bundle / name).write_bytes(b"%PDF-1.4 fake")
    return bundle


def test_writes_text_with_handwriting_section(tmp_path: Path):
    bundle = _make_nbn(tmp_path, hw_pages=["page1 ocr", "page2 ocr"], pdf_texts={}, pdfs=[])
    out = tmp_path / "TestNote.txt"
    raw_pdfs = tmp_path / "raw_pdfs"
    raw_pdfs.mkdir()
    extract_nbn(bundle, out, raw_pdfs)
    content = out.read_text()
    assert "TestNote" in content
    assert "Handwriting (OCR)" in content
    assert "page1 ocr" in content
    assert "page2 ocr" in content


def test_writes_text_with_pdf_section(tmp_path: Path):
    bundle = _make_nbn(
        tmp_path,
        hw_pages=[],
        pdf_texts={"ABCD1234-FAKE": "extracted pdf text"},
        pdfs=[],
    )
    out = tmp_path / "TestNote.txt"
    raw_pdfs = tmp_path / "raw_pdfs"
    raw_pdfs.mkdir()
    extract_nbn(bundle, out, raw_pdfs)
    content = out.read_text()
    assert "Embedded PDFs" in content
    assert "extracted pdf text" in content


def test_copies_raw_pdfs(tmp_path: Path):
    bundle = _make_nbn(
        tmp_path,
        hw_pages=[],
        pdf_texts={},
        pdfs=["doc1.pdf", "doc2.pdf"],
    )
    out = tmp_path / "TestNote.txt"
    raw_pdfs = tmp_path / "raw_pdfs"
    raw_pdfs.mkdir()
    extract_nbn(bundle, out, raw_pdfs)
    copied = sorted((raw_pdfs / "TestNote").glob("*.pdf"))
    assert [p.name for p in copied] == ["doc1.pdf", "doc2.pdf"]


def test_handles_bundle_with_no_handwriting_or_pdfs(tmp_path: Path):
    bundle = tmp_path / "Empty.nbn"
    bundle.mkdir()
    out = tmp_path / "Empty.txt"
    raw_pdfs = tmp_path / "raw_pdfs"
    raw_pdfs.mkdir()
    extract_nbn(bundle, out, raw_pdfs)
    # File written, has the header even if nothing else
    assert out.is_file()
    assert "Empty" in out.read_text()
