from pipeline.costs import CostTracker, image_cost, text_cost


def test_image_cost_dall_e_3():
    cost_std = image_cost("openai", "dall-e-3", size="1024x1024", quality="standard", count=1)
    assert cost_std == 0.040

    cost_hd = image_cost("openai", "dall-e-3", size="1024x1792", quality="hd", count=2)
    assert cost_hd == 0.240  # 0.120 * 2


def test_text_cost_gpt4o():
    cost = text_cost("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
    assert cost is not None
    assert cost > 0


def test_cost_tracker():
    tracker = CostTracker()
    tracker.add_text("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
    tracker.add_image("openai", "dall-e-3", size="1024x1024", quality="standard", count=1)
    meta = tracker.to_meta()
    assert meta["currency"] == "USD"
    assert meta["total_usd"] > 0
    assert len(meta["items"]) == 2
