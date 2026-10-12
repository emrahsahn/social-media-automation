"""Komut satırından tek tema için uçtan uca üretim.

Örnekler:
    python -m pipeline.cli --topic "Yeni sezon kahve" --count 2 --format post_4x5 \
        --overlay-text "Yeni sezon, yeni lezzet" --style lifestyle
    python -m pipeline.cli --topic "Test" --mock   # anahtar/harcama gerektirmez
"""

from __future__ import annotations

import argparse
import sys

from pipeline.config import MissingApiKeyError
from pipeline.formats import FORMATS, QUALITIES, STYLES
from pipeline.generate import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline.cli",
        description="Tek tema için uçtan uca sosyal medya gönderisi üretimi.",
    )
    parser.add_argument("--topic", required=True, help="Tema / konu (zorunlu)")
    parser.add_argument("--count", type=int, default=2, help="Görsel sayısı (1-4, varsayılan 2)")
    parser.add_argument("--style", default="product_photo", choices=STYLES, help="Görsel tipi")
    parser.add_argument("--format", default="post_4x5", choices=list(FORMATS), help="Hedef format")
    parser.add_argument("--overlay-text", default="", help="Görsel üzerine yazılacak metin (opsiyonel)")
    parser.add_argument("--notes", default="", help="Ek notlar (renk, ton vb.)")
    parser.add_argument("--quality", default="medium", choices=QUALITIES, help="gpt-image-1 kalitesi")
    parser.add_argument("--mock", action="store_true", help="API yerine sahte üretimle test")
    parser.add_argument("--out-root", default=None, help="Çıktı kök klasörü (varsayılan: ./outputs)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = {
        "topic": args.topic,
        "image_count": args.count,
        "style": args.style,
        "reference_image": None,
        "format": args.format,
        "overlay_text": args.overlay_text or None,
        "notes": args.notes or None,
        "quality": args.quality,
    }
    try:
        result = run_pipeline(payload, mock=args.mock, out_root=args.out_root)
    except MissingApiKeyError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    mode = "MOCK" if result["mock"] else "API"
    print(f"[{mode}] {len(result['posts'])} gönderi üretildi:")
    for post in result["posts"]:
        print(f"  - {post['dir']}")
    print("\nCaption:")
    print(f"  {result['caption']}")
    print("\nHashtag'ler:")
    print(f"  {' '.join(result['hashtags'])}")
    cost = result["cost"]
    print(f"\nTahmini maliyet: ${cost['total_usd']:.4f}")
    if cost.get("unpriced_items"):
        print(f"  (fiyatı bilinmeyen {cost['unpriced_items']} kalem usd=None olarak kaydedildi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
