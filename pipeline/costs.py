"""Üretim başına maliyet hesabı ve meta.json'a işlenecek maliyet kaydı.

FİYAT TABLOSU HAKKINDA
----------------------
Aşağıdaki birim fiyatlar 2026-10-10 itibarıyla YAKLAŞIK değerlerdir; resmi
fiyat sayfasından doğrulanmadan tek kaynak sayılmamalıdır. Sağlayıcı/model
seçimi netleşince (Sonraki Adımlar #3) bu tablo güncellenecek. Fiyatı
bilinmeyen model için uydurma tutar üretilmez: kalem `usd: None` olarak
kaydedilir ve meta'da `unpriced_items` sayısı belirtilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PRICING_NOTE = (
    "Fiyatlar 2026-10-10 tarihli yaklaşık tablodan; sağlayıcı seçilince resmi "
    "fiyat sayfasından doğrulanmalı."
)

# (sağlayıcı, model) -> {(boyut, kalite): görsel başı USD}
# ("default", "default") anahtarı, tabloda tam eşleşme yoksa kullanılır.
IMAGE_PRICES: dict[tuple[str, str], dict[tuple[str, str], float]] = {
    ("openai", "dall-e-3"): {
        ("1024x1024", "standard"): 0.040,
        ("1024x1024", "hd"): 0.080,
        ("1024x1792", "standard"): 0.080,
        ("1024x1792", "hd"): 0.120,
        ("default", "default"): 0.080,
    },
    ("openai", "dall-e-2"): {
        ("1024x1024", "standard"): 0.020,
        ("default", "default"): 0.020,
    },
    ("openai", "gpt-image-1"): {
        ("1024x1024", "low"): 0.011,
        ("1024x1024", "medium"): 0.042,
        ("1024x1024", "high"): 0.167,
        ("1024x1536", "low"): 0.016,
        ("1024x1536", "medium"): 0.063,
        ("1024x1536", "high"): 0.250,
        ("default", "default"): 0.042,
    },
}

# (sağlayıcı, model) -> (girdi USD / 1M token, çıktı USD / 1M token)
TEXT_PRICES: dict[tuple[str, str], tuple[float, float]] = {
    ("openai", "gpt-4o"): (2.50, 10.00),
    ("anthropic", "claude-sonnet-4-5"): (3.00, 15.00),
    ("anthropic", "claude-3-5-sonnet-20241022"): (3.00, 15.00),
    ("anthropic", "claude-3-5-sonnet"): (3.00, 15.00),
}


def image_cost(
    provider: str,
    model: str,
    *,
    size: str | None = None,
    quality: str | None = None,
    count: int = 1,
) -> float | None:
    """Görsel başına fiyat × adet; kombinasyon tabloda yoksa None."""
    table = IMAGE_PRICES.get((provider, model))
    if not table:
        return None
    unit = table.get((size, quality))
    if unit is None:
        unit = table.get((size, "default")) or table.get(("default", "default"))
    if unit is None:
        return None
    return round(unit * count, 4)


def text_cost(
    provider: str,
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    """Token bazlı metin maliyeti (USD); model tabloda yoksa None."""
    prices = TEXT_PRICES.get((provider, model))
    if not prices:
        return None
    input_price, output_price = prices
    return round(
        (input_tokens / 1_000_000) * input_price
        + (output_tokens / 1_000_000) * output_price,
        6,
    )


@dataclass
class CostTracker:
    """Bir üretim akışındaki harcamaları toplar; `to_meta()` ile meta.json'a girer."""

    items: list[dict] = field(default_factory=list)

    def add_image(
        self,
        provider: str,
        model: str,
        *,
        size: str | None = None,
        quality: str | None = None,
        count: int = 1,
    ) -> float | None:
        """Görsel üretim kalemini kaydeder; hesaplanan USD tutarını döner."""
        usd = image_cost(provider, model, size=size, quality=quality, count=count)
        self.items.append(
            {
                "kind": "image",
                "provider": provider,
                "model": model,
                "size": size,
                "quality": quality,
                "count": count,
                "usd": usd,
            }
        )
        return usd

    def add_text(
        self,
        provider: str,
        model: str,
        *,
        input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        """Metin (prompt/caption) üretim kalemini kaydeder; USD tutarını döner."""
        usd = text_cost(
            provider, model, input_tokens=input_tokens, output_tokens=output_tokens
        )
        self.items.append(
            {
                "kind": "text",
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "usd": usd,
            }
        )
        return usd

    @property
    def total_usd(self) -> float:
        """Fiyatı bilinen kalemlerin toplamı (USD)."""
        return round(sum(i["usd"] for i in self.items if i["usd"] is not None), 6)

    def to_meta(self) -> dict:
        """meta.json'a yazılacak `cost` bloğunu üretir."""
        meta: dict = {
            "currency": "USD",
            "items": self.items,
            "total_usd": self.total_usd,
            "pricing_note": PRICING_NOTE,
        }
        unpriced = sum(1 for i in self.items if i["usd"] is None)
        if unpriced:
            meta["unpriced_items"] = unpriced
        return meta
