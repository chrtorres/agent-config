"""Open the generated comparison PNG in a desktop browser window."""

import argparse
from pathlib import Path
import webbrowser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--browser", help="Browser name registered by Python's webbrowser module")
    args = parser.parse_args()
    comparison = args.output_dir.resolve() / "comparison.png"
    if not comparison.is_file():
        parser.error(f"Comparison PNG is missing: {comparison}")
    try:
        browser = webbrowser.get(args.browser)
        opened = browser.open_new(comparison.as_uri())
    except webbrowser.Error as exc:
        parser.exit(1, f"Desktop browser unavailable: {exc}\n")
    if not opened:
        parser.exit(1, "Desktop browser declined the window request.\n")
    print(f"Requested a browser window for {comparison}")


if __name__ == "__main__":
    main()
