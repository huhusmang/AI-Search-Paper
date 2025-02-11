import json
import sys
from pathlib import Path

sys.path.append(".")


def load_enriched_data(enriched_dir: str = "data/enriched"):
    """Load all enriched data into a dictionary keyed by title"""
    enriched_data = {}
    enriched_path = Path(enriched_dir)

    for conf_dir in enriched_path.iterdir():
        if not conf_dir.is_dir():
            continue

        for year_file in conf_dir.glob("*.json"):
            with open(year_file) as f:
                data = json.load(f)
                for paper in data:
                    if (
                        paper.get("info", {}).get("type")
                        == "Conference and Workshop Papers"
                    ):
                        title = paper["info"].get("title")
                        if title:
                            enriched_data[title] = paper

    return enriched_data


def update_output_files(
    output_dir: str = "data/output", enriched_dir: str = "data/enriched"
):
    """Update existing output files with correct ee URLs and keys from enriched data"""
    output_path = Path(output_dir)
    enriched_data = load_enriched_data(enriched_dir)

    # Recursively find all .jsonl files
    for jsonl_file in output_path.rglob("*.jsonl"):
        updated_papers = []
        modified = False

        # Read and update each paper
        with open(jsonl_file) as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    paper = json.loads(line)
                    if paper:
                        # Look up enriched data by title
                        enriched_paper = enriched_data.get(paper["title"])
                        if enriched_paper:
                            paper["key"] = enriched_paper["info"].get(
                                "key", "N/A"
                            )
                            paper["keywords"] = enriched_paper["info"].get(
                                "keywords", []
                            )
                            modified = True
                    updated_papers.append(paper)

        # Write back updated papers if modified
        if modified:
            with open(jsonl_file, "w") as f:
                for paper in updated_papers:
                    if paper:  # Skip empty entries
                        f.write(json.dumps(paper) + "\n")
            print(f"Updated {jsonl_file}")


if __name__ == "__main__":
    update_output_files()
