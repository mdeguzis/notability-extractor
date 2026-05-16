"""Tests for build.summaries."""

import json
from pathlib import Path

from notability_extractor.build import summaries
from notability_extractor.model import Summary


def test_write_json_lists_each_summary(tmp_path: Path):
    out = tmp_path / "summaries.json"
    summaries.write_json([
        Summary(title="T1", body="# T1\nbody1", source_file="T1.md"),
    ], out)
    data = json.loads(out.read_text())
    assert data["summaries"][0]["title"] == "T1"


def test_write_md_concatenates_bodies(tmp_path: Path):
    out = tmp_path / "summaries.md"
    summaries.write_md([
        Summary(title="T1", body="# T1\nbody1", source_file="T1.md"),
        Summary(title="T2", body="# T2\nbody2", source_file="T2.md"),
    ], out)
    body = out.read_text()
    assert "body1" in body
    assert "body2" in body
