"""ASCII frame generator CLI. Run with: python -m scarab.tools.ascii_generator"""

import argparse
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Generate ASCII frames from images for Scarab exercises")
    p.add_argument("--input", "-i", required=True, help="Input image path (PNG, JPG) or directory of images")
    p.add_argument("--output", "-o", required=True, help="Output directory for frames (e.g. data/frames/exercise_id)")
    p.add_argument("--size", "-s", choices=["small", "medium", "large"], default="medium",
                   help="Target size variant")
    p.add_argument("--width", "-w", type=int, default=60, help="ASCII output width in characters")
    return p.parse_args()


def image_to_ascii_naive(img_path: Path, width: int) -> str:
    """Convert image to ASCII using simple luminance mapping (no external deps)."""
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("Install pillow: pip install pillow")

    img = Image.open(img_path).convert("L")  # grayscale
    w, h = img.size
    ratio = h / w
    nwidth = width
    nheight = int(nwidth * ratio * 0.5)  # account for char aspect
    img = img.resize((nwidth, max(1, nheight)), Image.Resampling.LANCZOS)
    pixels = img.load()
    chars = " .:-=+*#%@"
    lines = []
    for y in range(img.height):
        row = []
        for x in range(img.width):
            v = pixels[x, y]
            idx = min(int(v / 256 * len(chars)), len(chars) - 1)
            row.append(chars[idx])
        lines.append("".join(row))
    return "\n".join(lines)


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Size-specific output
    size_dir = output_dir / args.size
    size_dir.mkdir(parents=True, exist_ok=True)

    widths = {"small": 40, "medium": 60, "large": 90}
    width = widths.get(args.size, args.width)

    if input_path.is_dir():
        images = sorted(input_path.glob("*.[pP][nN][gG]")) + sorted(input_path.glob("*.[jJ][pP][gG]"))
        for i, img_path in enumerate(images):
            ascii_frame = image_to_ascii_naive(img_path, width)
            out_file = size_dir / f"frame_{i:02d}.txt"
            out_file.write_text(ascii_frame)
            print(f"Wrote {out_file}")
    else:
        ascii_frame = image_to_ascii_naive(input_path, width)
        out_file = size_dir / f"frame_00.txt"
        out_file.write_text(ascii_frame)
        # Also write single frame at size root for simple case
        (output_dir / f"{args.size}.txt").write_text(ascii_frame)
        print(f"Wrote {out_file}")

    print(f"Done. Frames in {output_dir}")


if __name__ == "__main__":
    main()
