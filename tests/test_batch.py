import json
import pytest
from pathlib import Path
from pipeline.batch import load_batch_file, run_batch


def test_load_batch_file_txt(tmp_path: Path):
    txt_file = tmp_path / "topics.txt"
    txt_file.write_text("# Yorum satırı\nKahve Lansmanı\n\nSonbahar İndirimi\n", encoding="utf-8")
    items = load_batch_file(txt_file)
    assert len(items) == 2
    assert items[0]["topic"] == "Kahve Lansmanı"
    assert items[1]["topic"] == "Sonbahar İndirimi"


def test_load_batch_file_json(tmp_path: Path):
    json_file = tmp_path / "topics.json"
    data = [
        {"topic": "Özel Koleksiyon", "overlay_text": "Sınırlı Stok"},
        {"topic": "Yaz Sonu", "image_count": 1},
    ]
    json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    items = load_batch_file(json_file)
    assert len(items) == 2
    assert items[0]["topic"] == "Özel Koleksiyon"
    assert items[0]["overlay_text"] == "Sınırlı Stok"
    assert items[1]["image_count"] == 1


def test_load_batch_file_csv(tmp_path: Path):
    csv_file = tmp_path / "topics.csv"
    csv_file.write_text("topic,overlay_text,image_count\nÜrün Tanıtımı,Yeni Ürün,2\n", encoding="utf-8")
    items = load_batch_file(csv_file)
    assert len(items) == 1
    assert items[0]["topic"] == "Ürün Tanıtımı"
    assert items[0]["overlay_text"] == "Yeni Ürün"
    assert items[0]["image_count"] == 2


def test_run_batch_mock(tmp_path: Path):
    items = [
        {"topic": "Test Konu 1", "image_count": 1},
        {"topic": "Test Konu 2", "image_count": 1},
    ]
    res = run_batch(items, mock=True, out_root=tmp_path)
    assert res["total"] == 2
    assert res["successful_count"] == 2
    assert res["failed_count"] == 0
    assert len(res["successful"]) == 2
    assert res["mock"] is True
