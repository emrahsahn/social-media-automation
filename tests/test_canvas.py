from PIL import Image
from pipeline.canvas import to_canvas


def test_to_canvas_same_size():
    img = Image.new("RGB", (1080, 1350), color="red")
    out = to_canvas(img, 1080, 1350)
    assert out.size == (1080, 1350)


def test_to_canvas_aspect_ratio_crop():
    # 1024x1792 (9:16 approx) -> 1080x1350 (4:5)
    img = Image.new("RGB", (1024, 1792), color="blue")
    out = to_canvas(img, 1080, 1350)
    assert out.size == (1080, 1350)


def test_to_canvas_square():
    img = Image.new("RGB", (1024, 1024), color="green")
    out = to_canvas(img, 1080, 1080)
    assert out.size == (1080, 1080)
