import argparse
import sys
import csv
from pathlib import Path
from .ui_main import run_gui
from .export.streamdeck import export_profile


def _normalize_pagination(val: str) -> str:
    v = (val or "").strip().lower()
    if v in ("pages", "p"):
        return "Pages"
    if v in ("folders", "f"):
        return "Folders"
    raise argparse.ArgumentTypeError("pagination must be 'Pages' or 'Folders'")


def _normalize_alignment(val: str) -> str:
    v = (val or "").strip().lower()
    if v in ("bottom", "b"):
        return "bottom"
    if v in ("middle", "m", "center", "centre"):
        return "middle"
    if v in ("top", "t"):
        return "top"
    raise argparse.ArgumentTypeError("text-alignment must be 'bottom', 'middle', or 'top'")

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Stream Deck Profile Generator (GUI + CLI)"
    )
    parser.add_argument("--input", help="Input CSV with keys (optional)")
    parser.add_argument("--output", help="Output .streamDeckProfile (optional)")
    parser.add_argument("--device", choices=["mini","mk2","xl","generic"], default="xl",
                        help="Device preset")
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages/folders to generate")
    parser.add_argument("--pagination", type=_normalize_pagination, default="Pages",
                        help="Pagination mode: Pages|Folders")
    parser.add_argument("--text-alignment", type=_normalize_alignment, default="middle",
                        help="Text alignment on keys: bottom|middle|top")
    parser.add_argument("--font-family", default="", help="Font family (e.g., Verdana, Tahoma)")
    parser.add_argument("--font-size", type=int, default=12, help="Font size in px (6-24)")
    parser.add_argument("--font-style", default="", choices=["", "Regular", "Bold", "Italic", "Bold Italic"],
                        help="Font style")
    parser.add_argument("--font-underline", action="store_true", help="Enable underline")
    parser.add_argument("--no-show-title", action="store_true", help="Hide titles on buttons")
    args = parser.parse_args(argv)

    # CLI mode: if input and output provided and not forcing GUI
    if not args.gui and args.input and args.output:
        in_path = Path(args.input)
        out_path = Path(args.output)

        # Read CSV rows compatible with GUI's dump/load
        try:
            with in_path.open(newline='', encoding='utf-8') as f:
                rdr = csv.DictReader(f)
                rows = []
                profile_name = "Profile"
                for i, r in enumerate(rdr, start=1):
                    if i == 1:
                        name = (r.get('name') or '').strip()
                        if name:
                            profile_name = name
                    rows.append({
                        "include": str(r.get('include', '1')).strip() not in ('0','false','False',''),
                        "order": int(r.get('order') or i),
                        "original": (r.get('original') or r.get('label') or '').strip(),
                        "label": (r.get('label') or '').strip(),
                        "keystroke": (r.get('keystroke') or '').strip(),
                        "category": (r.get('category') or '').strip(),
                        "text_color": (r.get('text_color') or '#FFFFFF').strip(),
                        "split_label": str(r.get('split_label', '1')).strip() not in ('0','false','False',''),
                    })

            export_profile(
                rows=rows,
                out_path=str(out_path),
                profile_name=profile_name,
                device=args.device,
                max_pages=int(args.max_pages),
                text_alignment=args.text_alignment,
                pagination_mode=args.pagination,
                font_family=args.font_family,
                font_size=args.font_size,
                font_style=args.font_style,
                font_underline=args.font_underline,
                show_title=not args.no_show_title,
            )
            return 0
        except Exception as e:
            print(f"CLI error: {e}")
            return 1

    # Default to GUI
    return run_gui(args)

if __name__ == "__main__":
    sys.exit(main())
