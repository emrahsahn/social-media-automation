import pytest
from pipeline.brand import hex_to_rgb, _deep_merge, load_brand


def test_hex_to_rgb():
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("000000") == (0, 0, 0)
    assert hex_to_rgb("#FF00AA") == (255, 0, 170)
    with pytest.raises(ValueError):
        hex_to_rgb("invalid")


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    extra = {"b": {"d": 4, "e": 5}, "f": 6}
    merged = _deep_merge(base, extra)
    assert merged == {"a": 1, "b": {"c": 2, "d": 4, "e": 5}, "f": 6}


def test_load_brand():
    brand = load_brand()
    assert "font" in brand
    assert "text" in brand
    assert "strip" in brand
    assert len(brand["text"]["color"]) == 4  # RGBA
    assert len(brand["strip"]["color"]) == 3  # RGB
