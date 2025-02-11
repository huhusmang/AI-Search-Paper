import json
import logging
import time
from pathlib import Path

import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("log/dblp_download.log"),
        logging.StreamHandler(),
    ],
)

"""
CONFERENCE = {
    "USENIX Security": "uss",
    "S&P": "sp",
    "CCS": "ccs",
    "NDSS": "ndss",
}
"""
TEMPLATE = "https://dblp.org/search/publ/api?q=toc:db/conf/{conf}/{conf}{year}.bht:&h=1000&format={format}"
"""
Note: some confs have a special format, it is best to view the specific link format of the meeting dblp.org
TEMPLATE = "https://dblp.org/search/publ/api?q=toc:db/conf/kbse/{conf}{year}.bht:&h=1000&format={format}"
TEMPLATE = "https://dblp.org/search/publ/api?q=toc:db/journals/pacmse/pacmse1.bht%3A&h=1000&format=json"
"""


def get_conference_papers(
    conf: str, year: int, max_retries: int = 5, retry_delay: int = 10
) -> list:
    """Get papers from DBLP with retry mechanism."""
    url = TEMPLATE.format(conf=conf, year=year, format="json")

    for attempt in range(max_retries):
        try:
            res = requests.get(url, timeout=30)
            res.raise_for_status()

            data = res.json()["result"]["hits"]["hit"]
            if data:
                logging.info(
                    f"Successfully retrieved {len(data)} papers for {conf} {year}"
                )
                return data
            else:
                logging.warning(f"No papers found for {conf} {year}")
                return []

        except (RequestException, json.JSONDecodeError, KeyError) as e:
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
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    confs = ["uss", "sp", "ccs", "ndss"]
    years = [2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
    data_dir = Path("data/dblp")
    data_dir.mkdir(parents=True, exist_ok=True)

    failed_tasks = []

    for conf in confs:
        for year in years:
            logging.info(f"Processing {conf} {year}")

            data = get_conference_papers(conf, year)
            if not data:
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
