import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from httpcore import RemoteProtocolError
from semanticscholar import SemanticScholar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("log/sema_download.log"),
        logging.StreamHandler(),
    ],
)

sch = SemanticScholar()

CONFERENCE = {
    "uss": "USENIX Security Symposium",
    "sp": "IEEE Symposium on Security and Privacy",
    "ccs": "Conference on Computer and Communications Security",
    "ndss": "Network and Distributed System Security Symposium",
}


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle special types."""

    def default(self, obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def get_conference_papers(
    conf: str, year: int, max_retries: int = 3, retry_delay: int = 10
) -> list[dict[Any, Any]]:
    """Get papers with retry mechanism."""
    for attempt in range(max_retries):
        try:
            results = sch.search_paper(
                "*",
                venue=[conf],
                year=year,
                bulk=True,
            )

            # Only keep the _data field from each paper
            papers = []
            for paper in results.items:
                if hasattr(paper, "_data"):
                    papers.append(paper._data)
                else:
                    paper_dict = paper.__dict__.copy()
                    papers.append(paper_dict.get("_data", paper_dict))

            return papers

        except (RemoteProtocolError, Exception) as e:
            if attempt < max_retries - 1:
                logging.warning(
                    f"Attempt {attempt + 1} failed for {conf} {year}: {str(e)}"
                )
                time.sleep(retry_delay)
            else:
                logging.error(
                    f"Failed to get papers for {conf} {year} after {max_retries} attempts: {str(e)}"
                )
                return []


def save_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=4, cls=CustomJSONEncoder)


if __name__ == "__main__":
    confs = ["uss", "sp", "ccs", "ndss"]
    years = [2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
    data_dir = Path("data/sema")
    data_dir.mkdir(parents=True, exist_ok=True)

    failed_tasks = []

    for conf in confs:
        for year in years:
            logging.info(f"Processing {conf} {year}")
            data = get_conference_papers(CONFERENCE[conf], year)

            if not data:
                logging.error(f"Failed to get data for {conf} {year}")
                failed_tasks.append((conf, year))
                continue
            try:
                save_json(data, data_dir / f"{conf}/{year}.json")
                logging.info(f"Successfully saved data for {conf} {year}")
                time.sleep(5)  # Add delay between requests
            except Exception as e:
                logging.error(
                    f"Failed to save data for {conf} {year}: {str(e)}"
                )
                failed_tasks.append((conf, year))

    if failed_tasks:
        logging.warning("Failed tasks:")
        for conf, year in failed_tasks:
            logging.warning(f"- {conf} {year}")
    else:
        logging.info("All tasks completed successfully")
