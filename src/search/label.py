import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import instructor
from openai import OpenAI, OpenAIError
from pydantic import BaseModel
from tqdm import tqdm

from src.search.config import InstructorConfig, OpenaiConfig
from src.search.utils import call_llm


class Keywords(BaseModel):
    keywords: list[str]


class KeywordExtractor:
    def __init__(
        self,
        enriched_dir: str = "data/enriched",
        cache_dir: str = "data/cache/keywords",
        max_workers: int = 5,
    ):
        self.enriched_dir = Path(enriched_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers

    def _extract_keywords(
        self, title: str, abstract: str, max_retries: int = 3
    ) -> Keywords | None:
        """Extract keywords from paper title and abstract using LLM"""
        prompt = f"""
                    Title: {title}
                    Abstract: {abstract}
                    Based on the provided paper title and abstract, extract 5 keywords prioritized as follows: first, provide keywords that represent the research domain (avoiding overly broad terms like "security", "machine learning", "deep learning", "neural networks" etc.), followed by keywords that represent the research problem. The keywords should be concise and accurately capture the research domain and core issues of the provided paper. The output format should be only a list of keywords, just as follows:
                    [keyword1, keyword2, keyword3, keyword4, keyword5]

                    EXAMPLE INPUT: 
                    Title: "MACE: Detecting Privilege Escalation Vulnerabilities in Web Applications"
                    Abstract: "We explore the problem of identifying unauthorized privilege escalation instances in a web application. These vulnerabilities are typically caused by missing or incorrect authorizations in the server side code of a web application. The problem of identifying these vulnerabilities is compounded by the lack of an access control policy specification in a typical web application, where the only supplied documentation is in fact its source code. This makes it challenging to infer missing checks that protect a web application’s sensitive resources. To address this challenge, we develop a notion of authorization context consistency, which is satisfied when a web application consistently enforces its authorization checks across the code. We then present an approach based on program analysis to check for authorization state consistency in a web application. Our approach is implemented in a tool called MACE that uncovers vulnerabilities that could be exploited in the form of privilege escalation attacks. In particular, MACE is the first tool reported in the literature to identify a new class of web application vulnerabilities called Horizontal Privilege Escalation (HPE) vulnerabilities. MACE works on large codebases, and discovers serious, previously unknown, vulnerabilities in 5 out of 7 web applications tested. Without MACE, a comparable human-driven security audit would require weeks of effort in code inspection and testing."
 
                    EXAMPLE OUTPUT:
                    ["Web Application Security", "Access Control", "Privilege Escalation", "Authorization Vulnerabilities", "Horizontal Privilege Escalation (HPE)"]
                    """

        messages = [{"role": "user", "content": prompt}]

        client = instructor.from_openai(
            OpenAI(base_url=OpenaiConfig.base_url, api_key=OpenaiConfig.api_key)
        )

        for attempt in range(max_retries):
            try:
                response = call_llm(messages=messages)
                keywords = client.chat.completions.create(
                    model=InstructorConfig.model_name,
                    response_model=Keywords,
                    messages=[{"role": "user", "content": response}],
                )
                return keywords
            except OpenAIError as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(
                        f"OpenAI API error: {str(e)}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    print(
                        f"Failed to extract keywords after {max_retries} attempts: {str(e)}"
                    )
                    return None
            except Exception as e:
                print(f"Unexpected error extracting keywords: {str(e)}")
                return None

    def _get_cache_path(self, conference: str, year: str) -> Path:
        """Generate cache file path for the conference and year"""
        return self.cache_dir / f"{conference}_{year}_keywords.json"

    def process_papers(
        self,
        conference: str | None = None,
        year: str | None = None,
        save_partial: bool = True,
    ) -> None:
        """
        Process papers and extract keywords

        Args:
            conference: Optional conference to process
            year: Optional year to process
            save_partial: Whether to save partial results periodically
        """
        # Load and filter papers
        conferences = (
            [conference]
            if conference
            else [d.name for d in self.enriched_dir.iterdir() if d.is_dir()]
        )

        for conf in conferences:
            conf_dir = self.enriched_dir / conf
            if not conf_dir.is_dir():
                continue

            years = (
                [year] if year else [f.stem for f in conf_dir.glob("*.json")]
            )

            for year in years:
                input_file = conf_dir / f"{year}.json"
                if not input_file.exists():
                    continue

                print(f"\nProcessing {conf} {year}...")
                cache_path = self._get_cache_path(conf, year)
                partial_path = cache_path.with_suffix(".partial.json")

                # Load data
                try:
                    with open(input_file) as f:
                        papers = json.load(f)
                        papers_count = len(papers)
                except Exception as e:
                    print(f"Error loading {input_file}: {e}")
                    continue

                # Load processed papers from partial results if they exist
                processed_papers = set()
                if save_partial and partial_path.exists():
                    try:
                        with open(partial_path) as f:
                            partial_data = json.load(f)
                            processed_papers = set(partial_data["processed"])
                        print(
                            f"Loaded {len(processed_papers)} processed papers from partial results"
                        )
                    except Exception as e:
                        print(f"Error loading partial results: {str(e)}")

                def process_paper(
                    paper: dict[str, Any],
                ) -> tuple[str, list[str]] | None:
                    paper_id = paper["info"].get("title", "")
                    if (
                        paper_id in processed_papers
                        or paper["info"].get("type") == "Editorship"
                    ):
                        return None

                    title = paper["info"].get("title", "")
                    abstract = paper["info"].get("abstract", "")

                    try:
                        result = self._extract_keywords(title, abstract)
                        if result:
                            print(result.keywords)
                            return paper_id, result.keywords
                    except Exception as e:
                        print(f"Error processing paper {title}: {str(e)}")
                    return None

                save_interval = 5
                with ThreadPoolExecutor(
                    max_workers=self.max_workers
                ) as executor:
                    future_to_paper = {
                        executor.submit(process_paper, paper): paper
                        for paper in papers
                    }

                    with tqdm(
                        total=len(papers), desc="Extracting keywords"
                    ) as pbar:
                        completed = 0
                        for future in as_completed(future_to_paper):
                            paper = future_to_paper[future]
                            try:
                                result = future.result()
                                if result:
                                    paper_id, keywords = result
                                    # Update paper with keywords
                                    for p in papers:
                                        if p["info"].get("title") == paper_id:
                                            p["info"]["keywords"] = keywords
                                            break
                                    processed_papers.add(paper_id)

                                # Save partial results periodically
                                completed += 1
                                if (
                                    save_partial
                                    and completed % save_interval == 0
                                ):
                                    # Save updated papers
                                    with open(input_file, "w") as f:
                                        json.dump(papers, f, indent=4)
                                    # Save partial progress
                                    partial_data = {
                                        "processed": list(processed_papers),
                                        "papers": papers,
                                    }
                                    with open(partial_path, "w") as f:
                                        json.dump(partial_data, f, indent=4)
                            except Exception as e:
                                print(f"Error processing future: {str(e)}")
                            pbar.update(1)

                with open(input_file, "w") as f:
                    json.dump(papers, f, indent=4)

                # if save_partial and partial_path.exists():
                #     partial_path.unlink()  # Remove partial results file

                print(f"Completed processing {conf} {year}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract keywords from papers in the security conference dataset"
    )
    parser.add_argument(
        "--conference",
        type=str,
        choices=["uss", "sp", "ccs", "ndss"],
        help="Optional: Specific conference to process",
    )
    parser.add_argument(
        "--year", type=str, help="Optional: Specific year to process"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of concurrent threads",
    )
    parser.add_argument(
        "--save-partial",
        action="store_true",
        help="Save partial results periodically",
    )

    args = parser.parse_args()

    extractor = KeywordExtractor(max_workers=args.max_workers)
    extractor.process_papers(
        conference=args.conference,
        year=args.year,
        save_partial=args.save_partial,
    )


if __name__ == "__main__":
    main()
