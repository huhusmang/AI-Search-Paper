import json
from collections import defaultdict
from pathlib import Path


def analyze_conference_data(conf: str) -> dict:
    """Analyze abstract availability for a conference."""
    conf_dir = Path("data/enriched") / conf
    stats = defaultdict(lambda: {"total": 0, "missing_abstract": 0})

    if not conf_dir.exists():
        print(f"Directory not found: {conf_dir}")
        return {}

    for file in sorted(conf_dir.glob("*.json")):
        year = file.stem  # Get year from filename
        try:
            with open(file) as f:
                papers = json.load(f)

            for paper in papers:
                if paper["info"]["type"] != "Conference and Workshop Papers":
                    continue
                stats[year]["total"] += 1
                if (
                    "info" not in paper
                    or "abstract" not in paper["info"]
                    or paper["info"]["abstract"] is None
                ):
                    stats[year]["missing_abstract"] += 1

        except Exception as e:
            print(f"Error processing {file}: {str(e)}")

    return stats


def print_summary_table(all_stats: dict):
    """Print a summary table of missing abstracts."""
    print("\n=== Missing Abstracts Summary ===")
    print(
        f"{'Conf':<6} {'Year':<6} {'Missing':<8} {'Total':<8} {'Percentage':<10}"
    )
    print("-" * 40)

    # Sort by conference and year
    for conf in sorted(all_stats.keys()):
        for year in sorted(all_stats[conf].keys(), reverse=True):
            total = all_stats[conf][year]["total"]
            missing = all_stats[conf][year]["missing_abstract"]
            # if missing > 0:  # Only show years with missing abstracts
            percentage = (missing / total * 100) if total > 0 else 0
            print(
                f"{conf:<6} {year:<6} {missing:<8} {total:<8} {percentage:.1f}%"
            )


def main():
    conferences = ["uss", "sp", "ccs", "ndss"]
    all_stats = {}

    for conf in conferences:
        stats = analyze_conference_data(conf)
        if stats:
            all_stats[conf] = stats

    print_summary_table(all_stats)


if __name__ == "__main__":
    main()
