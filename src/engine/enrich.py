import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("log/enrich.log"),
        logging.StreamHandler(),
    ],
)


def merge_sema_data(conf: str) -> dict:
    """Merge semantic scholar data for a conference across all years."""
    sema_dir = Path("data/sema") / conf
    merged_data = {}

    if not sema_dir.exists():
        logging.error(f"Directory not found: {sema_dir}")
        return merged_data

    for file in sema_dir.glob("*.json"):
        try:
            with open(file) as f:
                data = json.load(f)
                for paper in data:
                    if (
                        "externalIds" in paper
                        and "DBLP" in paper["externalIds"]
                    ):
                        # Use DBLP ID as key for matching
                        dblp_id = paper["externalIds"]["DBLP"]
                        merged_data[dblp_id] = {
                            "paperId": paper.get("paperId"),
                            "title": paper.get("title"),
                            "abstract": paper.get("abstract"),
                        }
        except Exception as e:
            logging.error(f"Error processing {file}: {str(e)}")

    return merged_data


def enrich_dblp_data(conf: str, sema_data: dict) -> None:
    """Enrich DBLP data with Semantic Scholar information."""
    dblp_dir = Path("data/dblp") / conf
    output_dir = Path("data/enriched") / conf
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dblp_dir.exists():
        logging.error(f"Directory not found: {dblp_dir}")
        return

    for file in dblp_dir.glob("*.json"):
        if file.name != "2024.json":
            continue
        try:
            with open(file) as f:
                dblp_papers = json.load(f)

            # Enrich each paper with semantic scholar data
            for paper in dblp_papers:
                if "info" in paper and "key" in paper["info"]:
                    dblp_id = paper["info"]["key"]
                    if dblp_id in sema_data:
                        paper["sema_paperId"] = sema_data[dblp_id]["paperId"]
                        paper["info"]["abstract"] = sema_data[dblp_id][
                            "abstract"
                        ]

            # Save enriched data
            output_file = output_dir / file.name
            with open(output_file, "w") as f:
                json.dump(dblp_papers, f, indent=4)

            logging.info(f"Successfully enriched and saved {file.name}")

        except Exception as e:
            logging.error(f"Error processing {file}: {str(e)}")


def main():
    confs = ["uss", "sp", "ccs", "ndss"]

    for conf in confs:
        logging.info(f"Processing conference: {conf}")

        # Step 1: Merge semantic scholar data
        logging.info(f"Merging semantic scholar data for {conf}")
        sema_data = merge_sema_data(conf)
        logging.info(f"Found {len(sema_data)} papers in semantic scholar data")

        # Step 2: Enrich DBLP data
        logging.info(f"Enriching DBLP data for {conf}")
        enrich_dblp_data(conf, sema_data)

    logging.info("Data enrichment completed")


if __name__ == "__main__":
    main()
