import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import datasets
import instructor
from openai import OpenAI, OpenAIError
from pydantic import BaseModel
from tqdm import tqdm

from src.search.config import InstructorConfig, OpenaiConfig
from src.search.utils import call_llm


class RelevanceCheck(BaseModel):
    relevant: bool


class PaperSemanticSearch:
    def __init__(
        self,
        enriched_dir: str = "data/enriched",
        cache_dir: str = "data/cache",
        max_workers: int = 5,
    ):
        """
        Initialize the semantic search engine

        Args:
            enriched_dir: Path to the enriched data directory
            cache_dir: Path to cache directory for storing search results
            max_workers: Maximum number of concurrent threads
        """
        self.enriched_dir = Path(enriched_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.dataset = self._load_dataset()

    def _load_dataset(self) -> datasets.Dataset:
        """Load and preprocess papers from enriched data"""
        papers = []

        # Load papers from all conferences
        for conf_dir in self.enriched_dir.iterdir():
            if not conf_dir.is_dir():
                continue

            conf = conf_dir.name
            for year_file in conf_dir.glob("*.json"):
                year = year_file.stem
                try:
                    with open(year_file) as f:
                        data = json.load(f)
                        for paper in data:
                            if (
                                paper["info"]["type"]
                                != "Conference and Workshop Papers"
                            ):
                                continue
                            papers.append(
                                {
                                    "title": paper["info"].get("title", ""),
                                    "abstract": paper["info"].get(
                                        "abstract", ""
                                    ),
                                    "year": year,
                                    "conf": conf,
                                    "url": paper["info"].get("ee", ""),
                                    "key": paper["info"].get("key", ""),
                                    "keywords": paper["info"].get(
                                        "keywords", []
                                    ),
                                }
                            )
                except Exception as e:
                    print(f"Error loading {year_file}: {e}")

        return datasets.Dataset.from_list(papers)

    def _filter_dataset(
        self, conference: str | None = None, year: str | None = None
    ) -> datasets.Dataset:
        """Filter dataset by conference and year"""
        filtered = self.dataset
        if conference:
            filtered = filtered.filter(lambda x: x["conf"] == conference)
        if year:
            filtered = filtered.filter(lambda x: x["year"] == year)
        return filtered

    def _get_paper_content(self, paper: dict[str, Any]) -> str:
        """Get formatted paper content for comparison"""
        return f"""Title: {paper["title"]}
                Abstract: {paper.get("abstract", "N/A")}"""

    def _extract_relevance_check(self, prompt: str) -> RelevanceCheck:
        client = instructor.from_openai(
            OpenAI(base_url=OpenaiConfig.base_url, api_key=OpenaiConfig.api_key)
        )

        response = client.chat.completions.create(
            model=InstructorConfig.model_name,
            response_model=RelevanceCheck,
            messages=[{"role": "user", "content": prompt}],
        )
        return response

    def _check_relevance(
        self, query: str, paper_content: str, max_retries: int = 3
    ) -> RelevanceCheck | None:
        """
        Use LLM to check if a paper is relevant to the query

        Args:
            query: Search query
            paper_content: Paper content to check
            max_retries: Maximum number of retry attempts for API calls

        Returns:
            RelevanceCheck object if successful, None if failed after retries
        """
        messages = [
            {
                "role": "system",
                "content": """You are an assistant that analyzes the relevance of academic papers based on their titles and abstracts. Your task is to determine whether a given paper is relevant to specific user-provided keywords or queries. Ensure a comprehensive understanding of both the paper content and the keywords/query before making a judgment. Base your judgment solely on the content of the paper title and abstract without referencing external information. 
                Respond with:
                    - 'yes' if the paper is relevant
                    - 'no' if it's not relevant""",
            },
            {
                "role": "user",
                "content": f"{paper_content}\nUser Keywords/Query: {query}",
            },
        ]

        for attempt in range(max_retries):
            try:
                response = call_llm(messages=messages)
                return self._extract_relevance_check(response)
            except OpenAIError as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    print(
                        f"OpenAI API error: {str(e)}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    print(
                        f"Failed to check relevance after {max_retries} attempts: {str(e)}"
                    )
                    return None
            except Exception as e:
                print(f"Unexpected error checking relevance: {str(e)}")
                return None

    def _get_cache_path(
        self, query: str, conference: str | None = None, year: str | None = None
    ) -> Path:
        """Generate cache file path for the query"""
        # Create a unique cache key based on query parameters
        cache_key = f"{query}"
        if conference:
            cache_key += f"_conf={conference}"
        if year:
            cache_key += f"_year={year}"

        cache_key = hashlib.md5(cache_key.encode()).hexdigest()
        return self.cache_dir / f"{cache_key}.json"

    def _get_output_dir(
        self,
        base_dir: str,
        query: str,
    ) -> Path:
        """Generate output directory for results

        Returns:
            output_dir
        """
        cache_key = hashlib.md5(f"{query}".encode()).hexdigest()

        base_output_dir = Path(base_dir) / cache_key
        base_output_dir.mkdir(parents=True, exist_ok=True)

        # result dir
        result_dir = base_output_dir / "results"
        result_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata file
        metadata_path = base_output_dir / "metadata.json"
        metadata = {
            "query": query,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        return base_output_dir, result_dir

    def _save_results(
        self,
        results: list[dict[str, Any]],
        output_dir: Path,
        conference: str | None = None,
        year: str | None = None,
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

    def _concat_results(self, output_dir: Path) -> Path:
        """Concatenate results from all files in the output directory"""
        concat_path = output_dir / "all_results.jsonl"
        with open(concat_path, "w") as outfile:
            for file_path in output_dir.glob("*.jsonl"):
                if file_path != concat_path:  # Skip the concat file itself
                    with open(file_path) as infile:
                        for line in infile:
                            outfile.write(line)
        return concat_path

    def search(
        self,
        query: str,
        conference: str | None = None,
        year: str | None = None,
        use_cache: bool = True,
        save_partial: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant papers based on the query

        Args:
            query: Search query or description of the topic
            conference: Optional conference to search in
            year: Optional year to search in
            use_cache: Whether to use cached results
            save_partial: Whether to save partial results periodically

        Returns:
            List of relevant papers
        """
        cache_path = self._get_cache_path(query, conference, year)
        partial_path = cache_path.with_suffix(".partial.json")

        # Try to load from cache first
        if use_cache and cache_path.exists():
            with open(cache_path) as f:
                return json.load(f)

        # Try to load partial results if they exist
        processed_papers = set()
        relevant_papers = []
        if save_partial and partial_path.exists():
            try:
                with open(partial_path) as f:
                    partial_data = json.load(f)
                    relevant_papers = partial_data["results"]
                    processed_papers = set(partial_data["processed"])
                print(
                    f"Loaded {len(relevant_papers)} papers from partial results"
                )
            except Exception as e:
                print(f"Error loading partial results: {str(e)}")

        # Filter dataset based on conference and year
        filtered_dataset = self._filter_dataset(conference, year)
        papers_list = list(filtered_dataset)

        def process_paper(paper):
            if paper["title"] in processed_papers:
                return None

            paper_content = self._get_paper_content(paper)
            try:
                result = self._check_relevance(query, paper_content)
                if result and result.relevant:
                    return {
                        "title": paper.get("title", "N/A"),
                        "abstract": paper.get("abstract", "N/A"),
                        "year": paper.get("year", "N/A"),
                        "conf": paper.get("conf", "N/A"),
                        "url": paper.get("url", "N/A"),
                        "key": paper.get("key", "N/A"),
                        "keywords": paper.get("keywords", []),
                    }
            except Exception as e:
                print(
                    f"Error processing paper {paper.get('title', 'Unknown')}: {str(e)}"
                )
            return None

        save_interval = 10  # Save partial results every 10 papers
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_paper = {
                executor.submit(process_paper, paper): paper
                for paper in papers_list
            }

            with tqdm(total=len(papers_list), desc="Searching papers") as pbar:
                completed = 0
                for future in as_completed(future_to_paper):
                    paper = future_to_paper[future]
                    try:
                        result = future.result()
                        if result:
                            relevant_papers.append(result)
                        processed_papers.add(paper["title"])

                        # Save partial results periodically
                        completed += 1
                        if save_partial and completed % save_interval == 0:
                            partial_data = {
                                "results": relevant_papers,
                                "processed": list(processed_papers),
                            }
                            with open(partial_path, "w") as f:
                                json.dump(partial_data, f, indent=4)
                    except Exception as e:
                        print(f"Error processing future: {str(e)}")
                    pbar.update(1)

        # Save final results and clean up partial file
        with open(cache_path, "w") as f:
            json.dump(relevant_papers, f, indent=4)

        if save_partial and partial_path.exists():
            partial_path.unlink()  # Remove partial results file

        return relevant_papers


class PaperSearchRunner:
    def __init__(
        self,
        query: str,
        output_dir: str = "data/outputs",
        conference: str | None = None,
        years: str | None = None,
        max_workers: int = 10,
        use_cache: bool = True,
        save_partial: bool = True,
    ):
        """
        Initialize the paper search runner

        Args:
            query: Search query or description
            output_dir: Directory for output files
            conference: Optional conference to search in (uss, sp, ccs, ndss)
            years: Optional years string (e.g., '2015,2016,2015-2022')
            max_workers: Maximum number of concurrent threads
            use_cache: Whether to use cached results
            save_partial: Whether to save partial results
        """
        self.query = query
        self.conference = conference
        self.years = self._parse_years(years)
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.save_partial = save_partial
        self.output_dir = output_dir

        self.searcher = PaperSemanticSearch(max_workers=max_workers)

    def _parse_years(self, years_str: str | None) -> list[int]:
        """Parse years string into a list of years"""
        if not years_str:
            return list(range(2015, 2025))

        years = set()
        for part in years_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                try:
                    start_year = int(start)
                    end_year = int(end)
                    if start_year > end_year:
                        raise ValueError(
                            f"Start year {start_year} is after end year {end_year}."
                        )
                    years.update(range(start_year, end_year + 1))
                except ValueError as ve:
                    print(f"Invalid year range '{part}': {ve}")
            else:
                try:
                    years.add(int(part))
                except ValueError:
                    print(f"Invalid year '{part}'. Skipping.")
        return sorted(years)

    def run(self):
        """
        Run the paper search process
        """
        base_output_dir, result_dir = self.searcher._get_output_dir(
            self.output_dir,
            self.query,
        )

        all_results = []
        for year in self.years:
            year_str = str(year)

            results = self.searcher.search(
                query=self.query,
                conference=self.conference,
                year=year_str,
                use_cache=self.use_cache,
                save_partial=self.save_partial,
            )

            if results:
                all_results.extend(results)
                output_path = self.searcher._save_results(
                    results, result_dir, self.conference, year_str
                )
                print(
                    f"\nFound {len(results)} relevant papers for year {year_str}"
                )
                if output_path:
                    print(f"Results saved to: {output_path}")

        # Save concatenated results
        self.searcher._concat_results(base_output_dir)

        return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Search for relevant papers in the security conference dataset"
    )
    parser.add_argument(
        "--query", type=str, required=True, help="Search query or description"
    )
    parser.add_argument(
        "--conference",
        type=str,
        choices=["uss", "sp", "ccs", "ndss"],
        help="Optional: Specific conference to search in",
    )
    parser.add_argument(
        "--years",
        type=str,
        help="Optional: Comma-separated list of years or ranges to search in (e.g., '2015,2016,2015-2022')",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/outputs",
        help="Directory for output files",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of concurrent threads",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable using cached results"
    )
    parser.add_argument(
        "--save-partial",
        action="store_true",
        help="Save partial results periodically",
    )

    args = parser.parse_args()

    runner = PaperSearchRunner(
        query=args.query,
        output_dir=args.output_dir,
        conference=args.conference,
        years=args.years,
        max_workers=args.max_workers,
        use_cache=not args.no_cache,
        save_partial=args.save_partial,
    )

    runner.run()


if __name__ == "__main__":
    main()
