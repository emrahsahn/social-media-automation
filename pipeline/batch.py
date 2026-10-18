"""Toplu üretim modülü ve CLI aracı.

Birden fazla konu/gönderi tanımını tek bir dosyadan (JSON, CSV veya TXT) okur,
her biri için uçtan uca akışı (run_pipeline) çalıştırır ve kümülatif rapor sunar.

Kullanım:
    python -m pipeline.batch --file topics.txt --mock
    python -m pipeline.batch --file posts.json --count 2 --mock
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from pipeline.formats import FORMATS, QUALITIES, STYLES
from pipeline.generate import run_pipeline


def load_batch_file(file_path: str | Path) -> list[dict[str, Any]]:
    """JSON, CSV veya satır bazlı TXT dosyasından toplu girdi listesi yükler.

    Dönen her eleman en az 'topic' anahtarını içeren bir sözlüktür.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Toplu üretim dosyası bulunamadı: {path}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []

    items: list[dict[str, Any]] = []

    if suffix == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, str):
                    entry = entry.strip()
                    if entry:
                        items.append({"topic": entry})
                elif isinstance(entry, dict) and entry.get("topic"):
                    items.append(entry)
        elif isinstance(data, dict):
            raw_list = data.get("items") or data.get("topics") or []
            for entry in raw_list:
                if isinstance(entry, str):
                    entry = entry.strip()
                    if entry:
                        items.append({"topic": entry})
                elif isinstance(entry, dict) and entry.get("topic"):
                    items.append(entry)
        else:
            raise ValueError("JSON dosyası bir dizi (list) veya 'items'/'topics' alanı içermelidir.")

    elif suffix == ".csv":
        reader = csv.DictReader(text.splitlines())
        if not reader.fieldnames or "topic" not in [f.strip() for f in reader.fieldnames]:
            raise ValueError("CSV dosyası en az 'topic' başlık sütununu içermelidir.")
        for row in reader:
            cleaned = {k.strip(): v.strip() for k, v in row.items() if k and v}
            if cleaned.get("topic"):
                if "image_count" in cleaned:
                    cleaned["image_count"] = int(cleaned["image_count"])
                items.append(cleaned)

    else:
        # Varsayılan: TXT (her satır bir konu, '#' ile başlayanlar yorum)
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                items.append({"topic": line})

    return items


def run_batch(
    items: list[dict[str, Any]],
    *,
    mock: bool = False,
    default_options: dict[str, Any] | None = None,
    out_root: Path | None = None,
    stop_on_error: bool = False,
) -> dict[str, Any]:
    """Tüm girdileri sırayla işler ve kümülatif sonuç döner."""
    defaults = default_options or {}
    successful: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    total_cost_usd = 0.0

    for idx, item in enumerate(items, start=1):
        payload = {**defaults, **item}
        topic = payload.get("topic", "")
        try:
            res = run_pipeline(payload, mock=mock, out_root=out_root)
            cost_meta = res.get("cost", {})
            total_cost_usd += float(cost_meta.get("total_usd") or 0.0)
            successful.append({
                "index": idx,
                "topic": topic,
                "posts_count": len(res.get("posts", [])),
                "posts": res.get("posts", []),
                "caption": res.get("caption", ""),
                "hashtags": res.get("hashtags", []),
                "cost": cost_meta,
            })
        except Exception as exc:
            err_entry = {"index": idx, "topic": topic, "error": str(exc)}
            failed.append(err_entry)
            if stop_on_error:
                break

    return {
        "total": len(items),
        "processed": len(successful) + len(failed),
        "successful_count": len(successful),
        "failed_count": len(failed),
        "successful": successful,
        "failed": failed,
        "total_cost_usd": round(total_cost_usd, 6),
        "mock": mock,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline.batch",
        description="Birden fazla tema için toplu sosyal medya gönderisi üretimi.",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Toplu girdi dosyası yolu (.txt, .json veya .csv)",
    )
    parser.add_argument("--count", type=int, default=2, help="Görsel sayısı (varsayılan: 2)")
    parser.add_argument("--style", default="product_photo", choices=STYLES, help="Görsel stili")
    parser.add_argument("--format", default="post_4x5", choices=list(FORMATS), help="Format")
    parser.add_argument(
        "--provider",
        default="openai",
        choices=("openai", "anthropic"),
        help="LLM sağlayıcısı",
    )
    parser.add_argument("--quality", default="standard", choices=QUALITIES, help="Görsel kalitesi")
    parser.add_argument("--mock", action="store_true", help="API harcamadan mock modda çalıştır")
    parser.add_argument("--stop-on-error", action="store_true", help="Hata durumunda dur")
    parser.add_argument("--out-root", default=None, help="Çıktı kök klasörü")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        items = load_batch_file(args.file)
    except Exception as exc:
        print(f"HATA (Dosya okunamadı): {exc}", file=sys.stderr)
        return 1

    if not items:
        print("Uyarı: Dosyada işlenecek konu bulunamadı.", file=sys.stderr)
        return 0

    mode_str = "MOCK" if args.mock else "GERÇEK API"
    print(f"\n🚀 Toplu Üretim Başlatıldı [{mode_str}] — Toplam {len(items)} konu")
    print("=" * 60)

    defaults = {
        "image_count": args.count,
        "style": args.style,
        "format": args.format,
        "provider": args.provider,
        "quality": args.quality,
    }

    out_root = Path(args.out_root) if args.out_root else None
    report = run_batch(
        items,
        mock=args.mock,
        default_options=defaults,
        out_root=out_root,
        stop_on_error=args.stop_on_error,
    )

    print("\n" + "=" * 60)
    print("📊 Toplu Üretim Özeti:")
    print(f"  Toplam Konu : {report['total']}")
    print(f"  Başarılı    : {report['successful_count']}")
    print(f"  Başarısız   : {report['failed_count']}")
    print(f"  Toplam Tutar: ${report['total_cost_usd']:.4f}")

    if report["failed"]:
        print("\n❌ Başarısız Öğeler:")
        for fail in report["failed"]:
            print(f"  - [{fail['index']}] {fail['topic']}: {fail['error']}")

    print("=" * 60)
    return 0 if report["failed_count"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
