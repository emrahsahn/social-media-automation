from PIL import Image
from pipeline.overlay import overlay_text, overlay_logo
from pipeline.brand import load_brand


def test_overlay_text_basic():
    img = Image.new("RGB", (1080, 1350), color="white")
    result = overlay_text(img, "Yeni Sezon Kahveler")
    assert result.size == (1080, 1350)
    assert result.mode == "RGB"


def test_overlay_text_alignment():
    img = Image.new("RGB", (1080, 1350), color="white")
    brand = load_brand()

    # Left alignment
    brand_left = dict(brand)
    brand_left["text"] = dict(brand["text"], align="left")
    res_left = overlay_text(img, "Sol Hizalı Metin", brand=brand_left)
    assert res_left.size == (1080, 1350)

    # Right alignment
    brand_right = dict(brand)
    brand_right["text"] = dict(brand["text"], align="right")
    res_right = overlay_text(img, "Sağ Hizalı Metin", brand=brand_right)
    assert res_right.size == (1080, 1350)


def test_overlay_empty_text():
    img = Image.new("RGB", (1080, 1350), color="white")
    res = overlay_text(img, "")
    assert res.size == (1080, 1350)


def test_overlay_logo():
    img = Image.new("RGB", (1080, 1350), color="blue")
    logo = Image.new("RGBA", (200, 100), color=(255, 255, 255, 200))

    # Test different positions
    for pos in ["top-left", "top-right", "bottom-left", "bottom-right", "center", "top-center"]:
        res = overlay_logo(img, logo, position=pos, scale=0.15, opacity=0.8)
        assert res.size == (1080, 1350)
        assert res.mode == "RGB"

