import pytest
from pathlib import Path
from PIL import Image
from pipeline.reference import validate_reference_image, analyze_reference


def test_validate_reference_nonexistent(tmp_path: Path):
    with pytest.raises(ValueError, match="bulunamadı"):
        validate_reference_image(tmp_path / "does_not_exist.jpg")


def test_validate_reference_invalid_ext(tmp_path: Path):
    bad_file = tmp_path / "test.txt"
    bad_file.write_text("hello")
    with pytest.raises(ValueError, match="desteklenmiyor"):
        validate_reference_image(bad_file)


def test_mock_analyze_reference(tmp_path: Path):
    img_path = tmp_path / "sample.png"
    Image.new("RGB", (200, 200), color="blue").save(img_path)

    analysis, usage = analyze_reference(img_path, mock=True)
    assert "style_summary" in analysis
    assert "color_palette" in analysis
    assert usage["provider"] == "mock"
