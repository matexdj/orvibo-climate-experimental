"""Build the local review ZIP from integration files and public guides."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from check_repository import DOMAIN, ROOT, inspect_repository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    issues = inspect_repository()
    if issues:
        parser.error("\n".join(issues))

    component = ROOT / "custom_components" / DOMAIN
    files = [
        *component.glob("*.py"),
        *component.glob("translations/*.json"),
        *component.glob("brand/*.png"),
        *(component / name for name in (
            "manifest.json", "strings.json", "LICENSE", "orvibo_server_ca.pem",
            "orvibo_client_cert.pem", "orvibo_client_key.pem",
        )),
        *(ROOT / name for name in (
            "README.md", "INSTALL.md", "CONTRIBUTING.md", "LICENSE",
            "RELEASE_NOTES_0.1.0.md", "VALIDATION.md",
        )),
    ]
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing:
        parser.error(f"Missing package files: {', '.join(missing)}")
    with ZipFile(args.output, "x", compression=ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT))
    print(f"Created {args.output} with {len(files)} files")


if __name__ == "__main__":
    main()
