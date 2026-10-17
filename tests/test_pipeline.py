import json
from pathlib import Path
from PIL import Image
from pipeline.generate import run_pipeline


def test_run_pipeline_mock(tmp_path: Path):
    payload = {
        "topic": "Doğal Kahve Çekirdekleri",
        "image_count": 2,
        "style": "lifestyle",
        "format": "post_4x5",
        "overlay_text": "Doğadan Fincana",
        "notes": "Sıcak ahşap tonları",
        "quality": "standard",
    }
    result = run_pipeline(payload, mock=True, out_root=tmp_path)
    assert result["mock"] is True
    assert len(result["posts"]) == 2

    # Check that post files exist
    post_1 = Path(result["posts"][0]["dir"])
    assert (post_1 / "background.png").is_file()
    assert (post_1 / "final.png").is_file()
    assert (post_1 / "caption.txt").is_file()
    assert (post_1 / "meta.json").is_file()

    meta = json.loads((post_1 / "meta.json").read_text(encoding="utf-8"))
    assert meta["format"] == "post_4x5"
    assert meta["canvas"] == [1080, 1350]
    assert "cost" in meta
    assert "post_estimated_usd" in meta["cost"]


def test_run_pipeline_with_reference_mock(tmp_path: Path):
    ref_image = tmp_path / "ref.png"
    Image.new("RGB", (300, 300), color="orange").save(ref_image)

    payload = {
        "topic": "Sonbahar İndirimi",
        "image_count": 1,
        "style": "minimal_flat",
        "reference_image": str(ref_image),
        "reference_mode": "b1",
        "format": "post_1x1",
        "overlay_text": "%30 İndirim",
        "quality": "standard",
    }
    result = run_pipeline(payload, mock=True, out_root=tmp_path)
    assert len(result["posts"]) == 1

    post_dir = Path(result["posts"][0]["dir"])
    meta = json.loads((post_dir / "meta.json").read_text(encoding="utf-8"))
    assert "reference" in meta
    assert meta["reference"]["mode"] == "b1"
