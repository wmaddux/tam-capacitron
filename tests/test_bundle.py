"""
Tests for bundle parser: list contents, find collectinfo, extract.
"""

import tempfile
import zipfile
from pathlib import Path

import pytest
from ingest.bundle import (
    list_bundle_contents,
    find_collectinfo_in_bundle,
    extract_collectinfo_from_bundle,
    extract_collectinfo_from_file,
)


def test_list_bundle_contents_empty_zip(tmp_path):
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        pass
    assert list_bundle_contents(zip_path) == []


def test_list_bundle_contents_with_collectinfo(tmp_path):
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("some/path/collectinfo.txt", b"fake collectinfo content")
        zf.writestr("logs/server.log", b"log line")
    names = list_bundle_contents(zip_path)
    assert "some/path/collectinfo.txt" in names
    assert "logs/server.log" in names


def test_find_collectinfo_in_bundle(tmp_path):
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("collectinfo.txt", b"content")
        zf.writestr("other.txt", b"other")
    found = find_collectinfo_in_bundle(zip_path)
    assert "collectinfo.txt" in found
    assert "other.txt" not in found


def test_extract_collectinfo_from_bundle(tmp_path):
    content = b"collectinfo data here"
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dir/collectinfo", content)
    extracted = extract_collectinfo_from_bundle(zip_path)
    assert extracted == content


def test_extract_collectinfo_from_bundle_no_collectinfo(tmp_path):
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("only_logs.log", b"log")
    with pytest.raises(ValueError, match="No collectinfo"):
        extract_collectinfo_from_bundle(zip_path)


def test_extract_collectinfo_from_file():
    data = b"raw collectinfo"
    import io
    extracted = extract_collectinfo_from_file(io.BytesIO(data))
    assert extracted == data


def test_list_bundle_contents_not_found():
    with pytest.raises(FileNotFoundError, match="not found"):
        list_bundle_contents("/nonexistent/path.zip")
