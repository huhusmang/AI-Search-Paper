import argparse
import json
import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from src.engine.spider.spider_manager import SpiderManager

# Configure logging
logger = logging.getLogger("engine.enrich_missing")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # File handler
    file_handler = logging.FileHandler("log/enrich_missing.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class PaperInfo(NamedTuple):
    """Paper information for processing"""

    conference: str
    year: str
    paper_index: int
    url: str


def find_papers_missing_abstract(
    enriched_dir: Path, conference: str | None = None, year: str | None = None
) -> Iterator[PaperInfo]:
    """
    Find all papers with missing abstracts in enriched data

    Args:
        enriched_dir: Path to enriched data directory
        conference: Optional conference name to filter
        year: Optional year to filter

    Yields:
        PaperInfo for papers missing abstracts
    """
    # Filter conferences if specified
    conf_dirs = (
        [enriched_dir / conference] if conference else enriched_dir.iterdir()
    )

    for conf_dir in conf_dirs:
        if not conf_dir.is_dir():
            continue

        conference = conf_dir.name
        # Filter years if specified
        json_files = (
            [conf_dir / f"{year}.json"] if year else conf_dir.glob("*.json")
        )

        for file in json_files:
            if not file.exists():
                logger.warning(f"File not found: {file}")
                continue

            try:
                with open(file) as f:
                    papers = json.load(f)

                year = file.stem  # Get year from filename
                for i, paper in enumerate(papers):
                    # Check if abstract is missing and URL exists
                    if (
                        "info" in paper
                        and "ee" in paper["info"]
                        and (
                            "abstract" not in paper["info"]
                            or not paper["info"]["abstract"]
                        )
                        and paper["info"]["type"] != "Editorship"
                    ):
                        yield PaperInfo(
                            conference, year, i, paper["info"]["ee"]
                        )

            except Exception as e:
                logger.error(f"Error processing {file}: {str(e)}")


def update_paper_abstract(
    file_path: Path, paper_index: int, abstract: str, pdf_url: str
) -> None:
    """
    Update paper abstract and PDF URL in the JSON file

    Args:
        file_path: Path to JSON file
        paper_index: Index of paper to update
        abstract: New abstract text
        pdf_url: URL to PDF file (empty string if not available)
    """
    try:
        # Read current data
        with open(file_path) as f:
            papers = json.load(f)

        # Update abstract and PDF URL
        papers[paper_index]["info"]["abstract"] = abstract
        papers[paper_index]["info"]["pdf_url"] = pdf_url

        # Save updated data
        with open(file_path, "w") as f:
            json.dump(papers, f, indent=4)

    except Exception as e:
        logger.error(f"Error updating {file_path}: {str(e)}")
        raise


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Update missing abstracts in enriched data"
    )
    parser.add_argument(
        "-c",
        "--conference",
        choices=["ccs", "ndss", "sp", "uss"],
        help="Conference to update (default: all conferences)",
    )
    parser.add_argument(
        "-y", "--year", help="Year to update (default: all years)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    enriched_dir = Path("data/enriched")
    if not enriched_dir.exists():
        logger.error("Enriched data directory not found")
        return

    # Statistics
    total_missing = 0
    updated = 0
    failed = 0

    # Process papers with missing abstracts
    for paper_info in find_papers_missing_abstract(
        enriched_dir, args.conference, args.year
    ):
        time.sleep(5)
        total_missing += 1
        logger.info(
            f"Processing {paper_info.conference} {paper_info.year} "
            f"paper {paper_info.paper_index}"
        )

        try:
            # Get spider for conference
            spider_manager = SpiderManager(paper_info.conference)

            # Get paper info
            result = spider_manager.get_paper_info(paper_info.url)

            if result and result["abstract"]:
                # Update paper with new abstract and PDF URL
                file_path = (
                    enriched_dir
                    / paper_info.conference
                    / f"{paper_info.year}.json"
                )
                update_paper_abstract(
                    file_path,
                    paper_info.paper_index,
                    result["abstract"],
                    result.get(
                        "pdf_url", ""
                    ),  # Use empty string if pdf_url not present
                )
                updated += 1
                logger.info(
                    f"Successfully updated abstract for {paper_info.url}"
                )
            else:
                failed += 1
                logger.warning(f"Failed to get abstract for {paper_info.url}")

        except Exception as e:
            failed += 1
            logger.error(f"Error processing {paper_info.url}: {str(e)}")

    # Log final statistics
    logger.info("Processing completed:")
    logger.info(f"Total papers missing abstracts: {total_missing}")
    logger.info(f"Successfully updated: {updated}")
    logger.info(f"Failed to update: {failed}")


if __name__ == "__main__":
    main()
