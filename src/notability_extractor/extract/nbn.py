"""Parse Notability .nbn bundles: handwriting OCR + PDF text + embedded PDFs."""

import plistlib
import shutil
import zipfile
from pathlib import Path
from typing import Any

from notability_extractor.utils import get_logger

log = get_logger(__name__)


def extract_nbn(bundle: Path, output_text_path: Path, raw_pdfs_dir: Path) -> None:
    """Render a .nbn bundle to text and copy embedded PDFs.

    Writes <note-name>.txt to output_text_path with handwriting OCR and PDF
    text sections. Copies all *.pdf files inside the bundle to
    raw_pdfs_dir/<note-name>/.
    """
    note_name = bundle.stem
    parts: list[str] = []
    parts.append("=" * 40)
    parts.append(f"  {note_name}")
    parts.append("=" * 40)
    parts.append("")

    hw_index = bundle / "HandwritingIndex" / "index.plist"
    if hw_index.is_file():
        parts.append("--- Handwriting (OCR) ---")
        parts.append("")
        parts.append(_extract_handwriting_text(hw_index))

    pdf_zip = bundle / "NBPDFIndex" / "PDFIndex.zip"
    if pdf_zip.is_file():
        parts.append("--- Embedded PDFs ---")
        parts.append("")
        parts.append(_extract_pdf_text(pdf_zip))

    output_text_path.write_text("\n".join(parts))

    pdfs = list(bundle.rglob("*.pdf"))
    if pdfs:
        dest = raw_pdfs_dir / note_name
        dest.mkdir(parents=True, exist_ok=True)
        for pdf in pdfs:
            shutil.copy2(pdf, dest / pdf.name)


def _extract_handwriting_text(plist_path: Path) -> str:
    with plist_path.open("rb") as f:
        data = plistlib.load(f)
    return "\n\n".join(_walk_for_text(data))


def _walk_for_text(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        if "text" in obj and isinstance(obj["text"], str):
            out.append(obj["text"])
        for v in obj.values():
            out.extend(_walk_for_text(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_walk_for_text(item))
    return out


def _extract_pdf_text(zip_path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith("PDFTextIndex.txt"):
                pdf_name = Path(name).parent.name
                parts.append(f"  [PDF: {pdf_name[:8]}...]")
                parts.append(zf.read(name).decode("utf-8", errors="replace"))
                parts.append("")
    return "\n".join(parts)
