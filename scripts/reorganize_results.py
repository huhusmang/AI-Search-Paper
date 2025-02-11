import hashlib
import json
import time
from pathlib import Path
from typing import Any


def create_hash_dir(query: str, base_dir: str) -> tuple[Path, dict[str, Any]]:
    """Create hash-based directory and metadata for the query"""
    # Create hash of query for directory name
    cache_key = hashlib.md5(query.encode()).hexdigest()

    # Create output directory
    output_dir = Path(base_dir) / cache_key
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create metadata
    metadata = {
        "query": query,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Save metadata
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    return output_dir


def save_results(
    results: list[dict[str, Any]], output_dir: Path, conference: str, year: str
) -> Path:
    """Save results to appropriate files"""
    if not results:
        return None

    # Create filename based on conference and year
    filename = f"{conference}_{year}.jsonl"
    output_path = output_dir / filename

    # Save results to jsonl
    with open(output_path, "w") as f:
        for paper in results:
            f.write(json.dumps(paper) + "\n")

    return output_path


def concat_results(output_dir: Path) -> Path:
    """Concatenate all results into a single file"""
    concat_path = output_dir / "all_results.jsonl"
    with open(concat_path, "w") as outfile:
        for file_path in output_dir.glob("*.jsonl"):
            if file_path != concat_path:  # Skip the concat file itself
                with open(file_path) as infile:
                    for line in infile:
                        outfile.write(line)
    return concat_path


def main():
    # Define paths
    old_base_dir = Path("data/output")
    new_base_dir = Path("data/output")

    # Define query
    query = "Papers on detecting access control vulnerabilities in web applications (such as authentication bypass, authorization bypass, privilege escalation, etc.)"

    # Create new directory structure
    output_dir = create_hash_dir(query, new_base_dir)

    # Process each conference directory
    conferences = ["ccs", "ndss", "sp", "uss"]
    years = range(2015, 2025)

    for conf in conferences:
        for year in years:
            old_file = (
                old_base_dir
                / conf
                / str(year)
                / "papers_on_detecting_access_control_vulnerabilities.jsonl"
            )

            if old_file.exists() and old_file.stat().st_size > 0:
                # Read papers from old file
                papers = []
                with open(old_file) as f:
                    for line in f:
                        if line.strip():  # Skip empty lines
                            papers.append(json.loads(line))

                if papers:
                    # Save to new location
                    save_results(papers, output_dir, conf, str(year))
                    print(f"Processed {conf} {year}: {len(papers)} papers")

    # Create concatenated results file
    concat_path = concat_results(output_dir)
    print(f"\nAll results concatenated to: {concat_path}")

    # Print summary
    total_files = len(list(output_dir.glob("*.jsonl")))
    print("\nReorganization complete:")
    print(f"- Output directory: {output_dir}")
    print(f"- Total files: {total_files}")


if __name__ == "__main__":
    main()
