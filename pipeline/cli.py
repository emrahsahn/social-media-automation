"""Komut satırından tek tema için uçtan uca üretim.

Örnekler:
    python -m pipeline.cli --topic "Yeni sezon kahve" --count 2 --format post_4x5 \
        --overlay-text "Yeni sezon, yeni lezzet" --style lifestyle
    python -m pipeline.cli --topic "Test" --mock   # anahtar/harcama gerektirmez
"""

from __future__ import annotations

import argparse
import sys

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from openai import APIError

from pipeline.config import MissingApiKeyError
from pipeline.formats import FORMATS, QUALITIES, STYLES
from pipeline.generate import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline.cli",
        description="Tek tema veya toplu sosyal medya gönderisi üretimi.",
    )
    parser.add_argument("--topic", default=None, help="Tema / konu (tekli üretimde zorunlu)")
    parser.add_argument("--batch-file", default=None, help="Toplu üretim girdi dosyası (.txt, .json, .csv)")
    parser.add_argument("--count", type=int, default=2, help="Görsel sayısı (1-4, varsayılan 2)")
    parser.add_argument("--style", default="product_photo", choices=STYLES, help="Görsel tipi")
    parser.add_argument("--format", default="post_4x5", choices=list(FORMATS), help="Hedef format")
    parser.add_argument("--overlay-text", default="", help="Görsel üzerine yazılacak metin (opsiyonel)")
    parser.add_argument("--notes", default="", help="Ek notlar (renk, ton vb.)")
    parser.add_argument(
        "--provider",
        default="openai",
        choices=("openai", "anthropic"),
        help="LLM / Vision sağlayıcısı (varsayılan: openai)",
    )
    parser.add_argument(
        "--reference-image",
        default=None,
        help="Referans görsel yolu (JPG/PNG/WebP, maks. 10 MB)",
    )
    parser.add_argument(
        "--reference-mode",
        default="b1",
        choices=("b1", "b2"),
        help="b1: stil çözümleme, prompt'a yansıt (varsayılan) | b2: doğrudan edit API",
    )
    parser.add_argument("--quality", default="standard", choices=QUALITIES, help="Görsel kalitesi (DALL-E 3: standard, hd)")
    parser.add_argument("--mock", action="store_true", help="API yerine sahte üretimle test")
    parser.add_argument("--out-root", default=None, help="Çıktı kök klasörü (varsayılan: ./outputs)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.batch_file:
        from pipeline.batch import main as batch_main
        batch_argv = ["--file", args.batch_file, "--count", str(args.count), "--style", args.style,
                      "--format", args.format, "--provider", args.provider, "--quality", args.quality]
        if args.mock:
            batch_argv.append("--mock")
        if args.out_root:
            batch_argv.extend(["--out-root", args.out_root])
        return batch_main(batch_argv)

    if not args.topic:
        print("HATA: --topic veya --batch-file argümanlarından biri belirtilmelidir.", file=sys.stderr)
        return 1

    payload = {
        "topic": args.topic,
        "image_count": args.count,
        "style": args.style,
        "provider": args.provider,
        "reference_image": args.reference_image,
        "reference_mode": args.reference_mode,
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
    except APIError as exc:
        print(f"HATA (API): {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

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
