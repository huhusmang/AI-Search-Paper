import argparse
import json
import os
from pathlib import Path
from typing import Any

from notion_client import Client
from rich.console import Console

console = Console()


class NotionClient:
    """A class to handle Notion database operations for academic papers."""

    def __init__(self, database_id: str):
        """Initialize the Notion client.

        Args:
            database_id: The ID of the target Notion database
        """
        self.database_id = database_id
        self.client = self._create_client()

    def _create_client(self) -> Client:
        """Create and return a Notion client instance."""
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise ValueError("NOTION_TOKEN environment variable is not set")
        return Client(auth=token)

    def _truncate_text(self, text: str | None, max_length: int) -> str:
        """Truncate text to max_length and add ellipsis if needed."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _create_authors_text(self, authors: list) -> str:
        """Convert authors list to a formatted string."""
        if not authors:
            return ""
        return ", ".join(authors)

    def add_paper(self, paper: dict[str, Any]) -> None:
        """Add a single paper to the Notion database.

        Args:
            paper: Dictionary containing paper information
        """
        # Prepare properties for Notion page
        properties = {
            "Title": {"title": [{"text": {"content": paper.get("title")}}]},
            "Abstract": {
                "rich_text": [
                    {
                        "text": {
                            "content": self._truncate_text(
                                paper.get("abstract"), 2000
                            )
                        }
                    }
                ]
            },
            "Year": {"select": {"name": paper.get("year")}},
            "Conference": {"select": {"name": paper.get("conf", "")}},
            "Keywords": {
                "multi_select": [
                    {"name": kw} for kw in paper.get("keywords", [])
                ]
            },
            "URL": {"url": paper.get("url", "")},
        }

        page_data = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
        }

        try:
            self.client.pages.create(**page_data)
            console.print(
                f"✅ Added paper: {paper.get('title')}", style="green"
            )
        except Exception as e:
            console.print(
                f"❌ Error adding paper '{paper.get('title')}': {str(e)}",
                style="red",
            )

    def import_papers(self, dir_path: str | Path, file_pattern: str) -> None:
        """Import papers from JSONL files in directory matching the pattern.

        Args:
            dir_path: Path to the directory containing JSONL files
            file_pattern: Pattern to match JSONL files (e.g., "papers.jsonl")
        """
        dir_path = Path(dir_path)
        if not dir_path.exists() or not dir_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        # Find all matching JSONL files recursively
        matching_files = list(dir_path.rglob(file_pattern))

        if not matching_files:
            console.print(
                f"❌ No files matching '{file_pattern}' found in {dir_path}",
                style="red",
            )
            return

        console.print(
            f"📂 Found {len(matching_files)} matching files to process",
            style="blue",
        )

        # Process each matching file
        for file_idx, jsonl_file in enumerate(matching_files, 1):
            console.print(
                f"\n📄 Processing file {file_idx}/{len(matching_files)}: {jsonl_file}",
                style="blue",
            )

            try:
                # Read papers from JSONL file
                papers = []
                with open(jsonl_file, encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            papers.append(json.loads(line))

                total = len(papers)
                console.print(
                    f"📚 Found {total} papers to import from {jsonl_file.name}",
                    style="blue",
                )

                # Import papers with progress tracking
                for paper_idx, paper in enumerate(papers, 1):
                    console.print(
                        f"Processing paper {paper_idx}/{total} from {jsonl_file.name}"
                    )
                    self.add_paper(paper)

            except Exception as e:
                console.print(
                    f"❌ Error processing file {jsonl_file}: {str(e)}",
                    style="red",
                )


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Import academic papers from JSONL files to Notion database"
    )
    parser.add_argument(
        "--database_id", required=True, help="Notion database ID"
    )
    parser.add_argument(
        "--input_dir",
        required=True,
        help="Directory containing JSONL files",
    )
    parser.add_argument(
        "--file_pattern",
        default="*.jsonl",
        help="Pattern to match JSONL files (default: *.jsonl)",
    )

    args = parser.parse_args()

    notion = NotionClient(database_id=args.database_id)
    notion.import_papers(args.input_dir, args.file_pattern)


if __name__ == "__main__":
    main()
