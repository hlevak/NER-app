#!/usr/bin/env python3
"""
Download all required wheels for offline installation on Windows x64 + Python 3.10/3.11.
Run this script on a machine with internet access before transferring to an isolated machine.

Usage:
    python download_wheels.py [--python-version 3.11] [--output-dir wheels]
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


SPACY_MODEL_URLS = {
    "ru_core_news_sm": (
        "https://github.com/explosion/spacy-models/releases/download/"
        "ru_core_news_sm-3.7.0/ru_core_news_sm-3.7.0-py3-none-any.whl"
    ),
    "ru_core_news_lg": (
        "https://github.com/explosion/spacy-models/releases/download/"
        "ru_core_news_lg-3.7.0/ru_core_news_lg-3.7.0-py3-none-any.whl"
    ),
}

PACKAGES = [
    "spacy==3.7.2",
    "flask==3.0.3",
    "flask-cors==4.0.1",
    "gunicorn==21.2.0",
    "label-studio-ml==1.0.9",
    "label-studio==1.22.0",
    "psycopg2-binary==2.9.9",
    "sqlalchemy==2.0.31",
    "requests==2.31.0",
    "python-dotenv==1.0.1",
    "pydantic==2.7.4",
    "thinc==8.2.4",
    "cymem==2.0.8",
    "preshed==3.0.9",
    "murmurhash==1.0.10",
    "blis==0.7.11",
    "srsly==2.4.8",
    "catalogue==2.0.10",
    "weasel==0.3.4",
    "confection==0.1.4",
    "typer==0.9.4",
    "wasabi==1.1.3",
    "smart-open==7.0.4",
]


def download_wheels(python_version: str, output_dir: Path, include_lg_model: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading wheels for Python {python_version} Windows x86_64")
    print(f"Output directory: {output_dir.resolve()}")

    py_ver_nodot = python_version.replace(".", "")

    cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(output_dir),
        "--platform", "win_amd64",
        "--python-version", py_ver_nodot,
        "--implementation", "cp",
        "--abi", f"cp{py_ver_nodot}",
        "--only-binary=:all:",
    ] + PACKAGES

    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        print("\nSome packages could not be downloaded as binary wheels.")
        print("Retrying without platform restriction for pure-python packages...")
        cmd_noplat = [
            sys.executable, "-m", "pip", "download",
            "--dest", str(output_dir),
        ] + PACKAGES
        subprocess.run(cmd_noplat, check=False)

    print("\nDownloading spaCy models...")
    models_to_download = ["ru_core_news_sm"]
    if include_lg_model:
        models_to_download.append("ru_core_news_lg")

    for model_name in models_to_download:
        url = SPACY_MODEL_URLS[model_name]
        model_file = output_dir / f"{model_name}-3.7.0-py3-none-any.whl"
        if model_file.exists():
            print(f"  {model_name}: already exists, skipping")
            continue
        print(f"  Downloading {model_name} from GitHub...")
        import urllib.request
        try:
            urllib.request.urlretrieve(url, model_file)
            print(f"  {model_name}: downloaded to {model_file}")
        except Exception as exc:
            print(f"  ERROR downloading {model_name}: {exc}")

    wheel_count = len(list(output_dir.glob("*.whl")))
    tar_count = len(list(output_dir.glob("*.tar.gz")))
    print(f"\nDownload complete!")
    print(f"  Wheels (.whl): {wheel_count}")
    print(f"  Source tarballs (.tar.gz): {tar_count}")
    print(f"  Total: {wheel_count + tar_count} packages")
    print(f"\nDirectory: {output_dir.resolve()}")
    print("\nTransfer the entire 'wheels' directory to the isolated machine and run install_offline.bat")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download wheels for offline NER installation")
    parser.add_argument("--python-version", default="3.11", choices=["3.10", "3.11"],
                        help="Python version (default: 3.11)")
    parser.add_argument("--output-dir", default="wheels",
                        help="Output directory for wheels (default: wheels/)")
    parser.add_argument("--include-lg-model", action="store_true",
                        help="Also download ru_core_news_lg model (large, ~550MB)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    download_wheels(args.python_version, output_dir, args.include_lg_model)


if __name__ == "__main__":
    main()
