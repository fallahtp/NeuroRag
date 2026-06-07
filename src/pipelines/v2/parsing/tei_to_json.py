from __future__ import annotations

from pathlib import Path
import argparse
import json
import re
import xml.etree.ElementTree as ET

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # src/
from config import settings

BASE_DIR = Path(__file__).resolve().parents[4]
# Paths come from config so a separate sample corpus can be processed via
# NEURORAG_INTERIM_DIR / NEURORAG_RAW_DIR.
FULLTEXT_TEI_DIR = settings.interim_dir / "tei_xml"
HEADER_TEI_DIR = settings.interim_dir / "header_tei_xml"
JSON_DIR = settings.interim_dir / "structured_json"
RAW_DIR = settings.raw_dir

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return normalize_space(" ".join(node.itertext()))


def paper_id_from_tei_path(tei_path: Path) -> str:
    name = tei_path.name
    if name.endswith(".header.tei.xml"):
        return name[:-15]
    if name.endswith(".tei.xml"):
        return name[:-8]
    return tei_path.stem


def filename_year_fallback(tei_path: Path) -> str:
    m = re.match(r"^((19|20)\d{2})_", paper_id_from_tei_path(tei_path))
    return m.group(1) if m else ""


def fallback_title_from_filename(tei_path: Path) -> str:
    stem = paper_id_from_tei_path(tei_path)
    parts = stem.split("_")
    if parts and re.fullmatch(r"(19|20)\d{2}", parts[0]):
        parts = parts[1:]
    return " ".join(parts).strip()


def output_path_for(fulltext_tei_path: Path) -> Path:
    rel = fulltext_tei_path.relative_to(FULLTEXT_TEI_DIR)
    rel_str = str(rel).replace(".tei.xml", ".json")
    out_path = JSON_DIR / rel_str
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def header_path_for_fulltext(fulltext_tei_path: Path) -> Path:
    rel = fulltext_tei_path.relative_to(FULLTEXT_TEI_DIR)
    rel_str = str(rel).replace(".tei.xml", ".header.tei.xml")
    return HEADER_TEI_DIR / rel_str


def source_pdf_for(fulltext_tei_path: Path) -> str:
    rel = fulltext_tei_path.relative_to(FULLTEXT_TEI_DIR)
    rel_str = str(rel).replace(".tei.xml", ".pdf")
    return str((RAW_DIR / rel_str).relative_to(BASE_DIR)).replace("\\", "/")


def source_tei_for(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def safe_parse_xml(path: Path) -> ET.Element | None:
    if not path.exists():
        return None
    try:
        tree = ET.parse(path)
        return tree.getroot()
    except ET.ParseError as e:
        print(f"[WARN] Could not parse XML: {path} -> {e}")
        return None
    except Exception as e:
        print(f"[WARN] Could not read XML: {path} -> {e}")
        return None


def first_nonempty_text(root: ET.Element | None, xpaths: list[str]) -> str:
    if root is None:
        return ""
    for xp in xpaths:
        node = root.find(xp, NS)
        text = node_text(node)
        if text:
            return text
    return ""


def first_nonempty_from_roots(roots: list[ET.Element | None], xpaths: list[str]) -> str:
    for root in roots:
        text = first_nonempty_text(root, xpaths)
        if text:
            return text
    return ""


def normalize_section_type(title: str, idx: int) -> str:
    t = title.lower().strip()

    mapping = [
        ("abstract", "abstract"),
        ("introduction", "introduction"),
        ("background", "background"),
        ("materials and methods", "methods"),
        ("material and methods", "methods"),
        ("methods", "methods"),
        ("methodology", "methods"),
        ("results and discussion", "results_discussion"),
        ("results", "results"),
        ("discussion", "discussion"),
        ("conclusion", "conclusion"),
        ("conclusions", "conclusion"),
        ("references", "references"),
        ("bibliography", "references"),
        ("acknowledg", "acknowledgements"),
        ("funding", "funding"),
        ("supplement", "supplement"),
    ]

    for needle, label in mapping:
        if needle in t:
            return label

    if idx == 1 and not t:
        return "body_opening"

    return "section"


def title_looks_weak(title: str, tei_path: Path) -> bool:
    title = normalize_space(title)
    if not title:
        return True

    if "_" in title:
        return True

    fallback = fallback_title_from_filename(tei_path)

    def squish(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", s.lower())

    if squish(title) == squish(fallback):
        return True

    if len(title.split()) <= 3:
        return True

    return False


def is_generic_heading(title: str) -> bool:
    t = normalize_space(title).lower()
    generic = {
        "abstract",
        "introduction",
        "background",
        "methods",
        "materials and methods",
        "results",
        "discussion",
        "conclusion",
        "conclusions",
        "references",
        "acknowledgements",
        "funding",
        "supplementary material",
        "supplement",
    }
    return t in generic


def is_plausible_title_candidate(title: str) -> bool:
    title = normalize_space(title)
    if not title:
        return False
    if title.lower().startswith("untitled section"):
        return False
    if is_generic_heading(title):
        return False
    if len(title.split()) < 5:
        return False
    if len(title.split()) > 30:
        return False

    bad_markers = [
        "volume ",
        "issue ",
        "www.",
        "doi:",
        "received",
        "accepted",
        "available online",
    ]
    lower = title.lower()
    if any(marker in lower for marker in bad_markers):
        return False

    return True


def looks_like_front_matter_text(text: str) -> bool:
    text = normalize_space(text)
    lower = text.lower()

    strong_markers = [
        "department of",
        "university",
        "institute",
        "corresponding author",
        "@",
        "available online",
        "received ",
        "accepted ",
        "published by",
        "copyright",
        "all rights reserved",
    ]
    if any(marker in lower for marker in strong_markers):
        return True

    if len(text) < 500:
        comma_count = text.count(",")
        semicolon_count = text.count(";")
        period_count = text.count(".")
        if comma_count + semicolon_count >= 6 and period_count <= 2:
            return True

    initials_pattern = re.findall(r"\b[A-Z]\.\s?[A-Z]?\.\s?[A-Za-z-]+", text)
    if len(initials_pattern) >= 3 and len(text) < 600:
        return True

    return False


def clean_keywords(keywords: list[str]) -> list[str]:
    cleaned = []
    seen = set()

    for kw in keywords:
        kw = normalize_space(kw)
        if not kw:
            continue
        if kw.lower().startswith("rrid:"):
            continue
        if len(kw) > 120:
            continue
        if kw not in seen:
            seen.add(kw)
            cleaned.append(kw)

    return cleaned


def extract_title(header_root: ET.Element | None, fulltext_root: ET.Element | None) -> str:
    return first_nonempty_from_roots(
        [header_root, fulltext_root],
        [
            ".//tei:teiHeader//tei:fileDesc//tei:titleStmt/tei:title[@type='main']",
            ".//tei:teiHeader//tei:fileDesc//tei:titleStmt/tei:title[@level='a']",
            ".//tei:teiHeader//tei:fileDesc//tei:titleStmt/tei:title",
            ".//tei:teiHeader//tei:sourceDesc//tei:biblStruct//tei:analytic/tei:title",
            ".//tei:teiHeader//tei:sourceDesc//tei:biblStruct//tei:monogr/tei:title",
            ".//tei:titleStmt/tei:title",
        ],
    )


def extract_authors_from_root(root: ET.Element | None) -> list[str]:
    if root is None:
        return []

    author_nodes = root.findall(
        ".//tei:teiHeader//tei:fileDesc//tei:sourceDesc//tei:author",
        NS,
    )
    if not author_nodes:
        author_nodes = root.findall(
            ".//tei:teiHeader//tei:fileDesc//tei:titleStmt//tei:author",
            NS,
        )

    authors = []
    seen = set()

    for author in author_nodes:
        pers = author.find(".//tei:persName", NS)

        if pers is not None:
            pieces = []

            for forename in pers.findall(".//tei:forename", NS):
                txt = node_text(forename)
                if txt:
                    pieces.append(txt)

            surname = pers.find(".//tei:surname", NS)
            surname_text = node_text(surname)
            if surname_text:
                pieces.append(surname_text)

            name = normalize_space(" ".join(pieces))
            if name and name not in seen:
                seen.add(name)
                authors.append(name)
                continue

        fallback = node_text(author)
        fallback_lower = fallback.lower()

        if any(marker in fallback_lower for marker in ["department of", "university", "institute", "@"]):
            continue

        if fallback and fallback not in seen:
            seen.add(fallback)
            authors.append(fallback)

    return authors


def extract_authors(header_root: ET.Element | None, fulltext_root: ET.Element | None) -> list[str]:
    header_authors = extract_authors_from_root(header_root)
    if header_authors:
        return header_authors
    return extract_authors_from_root(fulltext_root)


def extract_abstract(header_root: ET.Element | None, fulltext_root: ET.Element | None) -> str:
    for root in [fulltext_root, header_root]:
        if root is None:
            continue

        parts = []
        for node in root.findall(".//tei:teiHeader//tei:profileDesc//tei:abstract", NS):
            text = node_text(node)
            if text:
                parts.append(text)

        abstract = normalize_space(" ".join(parts))
        if abstract:
            return abstract

    return ""


def extract_keywords(header_root: ET.Element | None, fulltext_root: ET.Element | None) -> list[str]:
    for root in [header_root, fulltext_root]:
        if root is None:
            continue

        keywords = []

        for node in root.findall(".//tei:teiHeader//tei:profileDesc//tei:keywords//tei:term", NS):
            text = node_text(node)
            if text:
                keywords.append(text)

        if not keywords:
            for node in root.findall(".//tei:teiHeader//tei:profileDesc//tei:keywords", NS):
                text = node_text(node)
                if text:
                    parts = re.split(r";|,|\u2022", text)
                    keywords.extend([normalize_space(p) for p in parts if normalize_space(p)])

        cleaned = clean_keywords(keywords)
        if cleaned:
            return cleaned

    return []


def extract_doi(header_root: ET.Element | None, fulltext_root: ET.Element | None) -> str:
    for root in [header_root, fulltext_root]:
        if root is None:
            continue

        for node in root.findall(".//tei:teiHeader//tei:idno", NS):
            id_type = (node.attrib.get("type") or "").lower()
            text = node_text(node)
            if id_type == "doi" and text:
                return text
            if text.startswith("10."):
                return text

    return ""


def extract_year(header_root: ET.Element | None, fulltext_root: ET.Element | None, tei_path: Path) -> str:
    for root in [header_root, fulltext_root]:
        if root is None:
            continue

        for node in root.findall(".//tei:teiHeader//tei:date", NS):
            when = node.attrib.get("when", "")
            m = re.search(r"\b(19|20)\d{2}\b", when)
            if m:
                return m.group(0)

        for node in root.findall(".//tei:teiHeader//tei:date", NS):
            text = node_text(node)
            m = re.search(r"\b(19|20)\d{2}\b", text)
            if m:
                return m.group(0)

    return filename_year_fallback(tei_path)


def extract_raw_sections(fulltext_root: ET.Element | None) -> list[dict]:
    if fulltext_root is None:
        return []

    body = fulltext_root.find(".//tei:text/tei:body", NS)
    if body is None:
        return []

    sections = []
    sec_num = 1

    divs = body.findall(".//tei:div", NS)

    for div in divs:
        head = div.find("./tei:head", NS)
        section_title = node_text(head)

        paragraphs = []
        for p in div.findall("./tei:p", NS):
            text = node_text(p)
            if text:
                paragraphs.append(text)

        text = normalize_space("\n\n".join(paragraphs))
        if not text:
            continue

        sections.append(
            {
                "section_id": f"sec_{sec_num:03d}",
                "section_title": section_title or f"Untitled section {sec_num}",
                "section_type": normalize_section_type(section_title, sec_num),
                "text": text,
            }
        )
        sec_num += 1

    if sections:
        return sections

    paragraphs = []
    for p in body.findall(".//tei:p", NS):
        text = node_text(p)
        if text:
            paragraphs.append(text)

    if not paragraphs:
        return []

    block_size = 8
    fallback_sections = []

    for i in range(0, len(paragraphs), block_size):
        block = paragraphs[i:i + block_size]
        text = normalize_space("\n\n".join(block))
        fallback_sections.append(
            {
                "section_id": f"sec_{(i // block_size) + 1:03d}",
                "section_title": f"Body block {(i // block_size) + 1}",
                "section_type": "body",
                "text": text,
            }
        )

    return fallback_sections


def choose_best_title(extracted_title: str, raw_sections: list[dict], tei_path: Path) -> str:
    if not title_looks_weak(extracted_title, tei_path):
        return extracted_title

    for sec in raw_sections[:6]:
        section_title = normalize_space(sec.get("section_title", ""))
        section_text = normalize_space(sec.get("text", ""))

        if is_plausible_title_candidate(section_title) and looks_like_front_matter_text(section_text):
            return section_title

    for sec in raw_sections[:6]:
        section_title = normalize_space(sec.get("section_title", ""))
        if is_plausible_title_candidate(section_title):
            return section_title

    fallback = fallback_title_from_filename(tei_path)
    return fallback


def clean_sections(raw_sections: list[dict], chosen_title: str) -> list[dict]:
    cleaned = []
    new_idx = 1

    for sec in raw_sections:
        section_title = normalize_space(sec.get("section_title", ""))
        section_text = normalize_space(sec.get("text", ""))
        section_type = sec.get("section_type", "section")

        if not section_text:
            continue

        if len(section_text) < 40:
            continue

        drop_this = False

        if looks_like_front_matter_text(section_text):
            if section_title == chosen_title:
                drop_this = True
            elif section_type in {"section", "body_opening"} and len(section_text) < 700:
                drop_this = True

        if drop_this:
            continue

        cleaned.append(
            {
                "section_id": f"sec_{new_idx:03d}",
                "section_title": section_title or f"Untitled section {new_idx}",
                "section_type": section_type,
                "text": section_text,
            }
        )
        new_idx += 1

    return cleaned


def parse_paper(fulltext_tei_path: Path) -> dict:
    header_tei_path = header_path_for_fulltext(fulltext_tei_path)

    fulltext_root = safe_parse_xml(fulltext_tei_path)
    header_root = safe_parse_xml(header_tei_path)

    raw_sections = extract_raw_sections(fulltext_root)
    extracted_title = extract_title(header_root, fulltext_root)
    chosen_title = choose_best_title(extracted_title, raw_sections, fulltext_tei_path)
    cleaned_sections = clean_sections(raw_sections, chosen_title)

    return {
        "paper_id": paper_id_from_tei_path(fulltext_tei_path),
        "source_pdf": source_pdf_for(fulltext_tei_path),
        "source_fulltext_tei": source_tei_for(fulltext_tei_path),
        "source_header_tei": source_tei_for(header_tei_path) if header_tei_path.exists() else "",
        "metadata": {
            "title": chosen_title,
            "authors": extract_authors(header_root, fulltext_root),
            "abstract": extract_abstract(header_root, fulltext_root),
            "keywords": extract_keywords(header_root, fulltext_root),
            "doi": extract_doi(header_root, fulltext_root),
            "year": extract_year(header_root, fulltext_root, fulltext_tei_path),
        },
        "sections": cleaned_sections,
    }


def find_all_fulltext_tei_files() -> list[Path]:
    tei_files = sorted(FULLTEXT_TEI_DIR.rglob("*.tei.xml"))
    if not tei_files:
        raise FileNotFoundError(f"No fulltext TEI XML files found under: {FULLTEXT_TEI_DIR}")
    return tei_files


def write_json(data: dict, fulltext_tei_path: Path) -> Path:
    out_path = output_path_for(fulltext_tei_path)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tei", type=str, help="Path to one fulltext TEI XML file")
    args = parser.parse_args()

    if args.tei:
        tei_path = Path(args.tei)
        if not tei_path.is_absolute():
            tei_path = BASE_DIR / tei_path

        data = parse_paper(tei_path)
        out_path = write_json(data, tei_path)
        print(f"Saved: {out_path}")
        return

    tei_files = find_all_fulltext_tei_files()
    print(f"Found {len(tei_files)} fulltext TEI files")

    success = 0
    failed = 0

    for i, tei_path in enumerate(tei_files, start=1):
        try:
            print(f"[{i}/{len(tei_files)}] Parsing: {tei_path}")
            data = parse_paper(tei_path)
            out_path = write_json(data, tei_path)
            print(f"Saved: {out_path}")
            success += 1
        except Exception as e:
            print(f"[FAIL] {tei_path} -> {e}")
            failed += 1

    print(f"\nDone. Success: {success} | Failed: {failed}")


if __name__ == "__main__":
    main()