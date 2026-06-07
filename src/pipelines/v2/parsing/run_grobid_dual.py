from __future__ import annotations

from pathlib import Path
import argparse
import sys
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # src/
from config import settings

BASE_DIR = Path(__file__).resolve().parents[4]
# Paths come from config so a separate sample corpus can be parsed via
# NEURORAG_RAW_DIR / NEURORAG_INTERIM_DIR without touching a private corpus.
RAW_DIR = settings.raw_dir
FULLTEXT_TEI_DIR = settings.interim_dir / "tei_xml"
HEADER_TEI_DIR = settings.interim_dir / "header_tei_xml"
ERROR_DIR = settings.interim_dir / "grobid_errors"

# GROBID host is configurable so the parser can target a container on another
# host/port without editing the source. Override with the GROBID_URL env var.
GROBID_URL = settings.grobid_url
FULLTEXT_URL = f"{GROBID_URL}/api/processFulltextDocument"
HEADER_URL = f"{GROBID_URL}/api/processHeaderDocument"


def output_path_for(pdf_path: Path, base_dir: Path, suffix: str) -> Path:
    rel = pdf_path.relative_to(RAW_DIR).with_suffix(suffix)
    out_path = base_dir / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def error_path_for(pdf_path: Path, kind: str) -> Path:
    rel = pdf_path.relative_to(RAW_DIR).with_suffix(f".{kind}.error.txt")
    out_path = ERROR_DIR / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def looks_like_xml(text: str) -> bool:
    stripped = text.lstrip("\ufeff\r\n\t ")
    return (
        stripped.startswith("<?xml")
        or stripped.startswith("<TEI")
        or stripped.startswith("<tei:")
    )


def post_pdf_to_grobid(
    pdf_path: Path,
    url: str,
    data: dict | None = None,
) -> tuple[str, str]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        with pdf_path.open("rb") as f:
            files = {"input": (pdf_path.name, f, "application/pdf")}
            response = requests.post(
                url,
                files=files,
                data=data or {},
                headers={"Accept": "application/xml"},
                timeout=600,
            )
    except (requests.ConnectionError, requests.Timeout) as e:
        raise RuntimeError(
            f"Could not reach GROBID at {url} ({e.__class__.__name__}). "
            "Is the GROBID container running? Set the GROBID_URL environment "
            "variable to point at a different host."
        ) from e

    text = response.text
    content_type = response.headers.get("Content-Type", "")

    if response.status_code != 200:
        raise RuntimeError(
            f"GROBID failed for {pdf_path.name} | "
            f"url={url} | status={response.status_code} | "
            f"content_type={content_type} | body={text[:500]}"
        )

    return text, content_type


def save_error_payload(
    pdf_path: Path,
    kind: str,
    payload: str,
    content_type: str,
) -> Path:
    out_path = error_path_for(pdf_path, kind)
    out_path.write_text(
        f"CONTENT-TYPE: {content_type}\n\n{payload}",
        encoding="utf-8",
        errors="replace",
    )
    return out_path


def process_one_pdf(pdf_path: Path, overwrite: bool = False) -> tuple[Path | None, Path | None]:
    fulltext_out = output_path_for(pdf_path, FULLTEXT_TEI_DIR, ".tei.xml")
    header_out = output_path_for(pdf_path, HEADER_TEI_DIR, ".header.tei.xml")

    if not overwrite and fulltext_out.exists() and header_out.exists():
        print(f"[SKIP] Already exists: {pdf_path}")
        return fulltext_out, header_out

    header_text, header_ct = post_pdf_to_grobid(
        pdf_path,
        HEADER_URL,
        data={
            "consolidateHeader": "0",
            "includeRawAffiliations": "1",
        },
    )

    fulltext_text, fulltext_ct = post_pdf_to_grobid(
        pdf_path,
        FULLTEXT_URL,
        data={
            "consolidateHeader": "0",
            "consolidateCitations": "0",
            "includeRawAffiliations": "1",
        },
    )

    if looks_like_xml(fulltext_text):
        fulltext_out.write_text(fulltext_text, encoding="utf-8")
    else:
        err = save_error_payload(pdf_path, "fulltext", fulltext_text, fulltext_ct)
        raise RuntimeError(f"Fulltext response was not XML. Saved raw response to: {err}")

    if looks_like_xml(header_text):
        header_out.write_text(header_text, encoding="utf-8")
    else:
        err = save_error_payload(pdf_path, "header", header_text, header_ct)
        print(f"[WARN] Header response was not XML for {pdf_path.name}. Saved raw response to: {err}")
        header_out = None

    return fulltext_out, header_out


def find_all_pdfs() -> list[Path]:
    pdfs = sorted(RAW_DIR.rglob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found under: {RAW_DIR}")
    return pdfs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=str, help="Path to one PDF")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reprocess files even if outputs already exist",
    )
    args = parser.parse_args()

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.is_absolute():
            pdf_path = BASE_DIR / pdf_path

        print(f"Processing one PDF: {pdf_path}")
        try:
            fulltext_out, header_out = process_one_pdf(pdf_path, overwrite=args.overwrite)
        except Exception as e:
            raise SystemExit(f"[FAIL] {pdf_path} -> {e}")
        print(f"Saved fulltext TEI: {fulltext_out}")
        print(f"Saved header TEI:   {header_out}")
        return

    pdfs = find_all_pdfs()
    print(f"Found {len(pdfs)} PDFs")

    success = 0
    failed = 0

    for i, pdf_path in enumerate(pdfs, start=1):
        try:
            print(f"[{i}/{len(pdfs)}] Processing: {pdf_path}")
            fulltext_out, header_out = process_one_pdf(pdf_path, overwrite=args.overwrite)
            print(f"  fulltext -> {fulltext_out}")
            print(f"  header   -> {header_out}")
            success += 1
        except Exception as e:
            print(f"[FAIL] {pdf_path} -> {e}")
            failed += 1

    print(f"\nDone. Success: {success} | Failed: {failed}")


if __name__ == "__main__":
    main()