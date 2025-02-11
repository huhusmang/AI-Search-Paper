import json
import re
import time

import cloudscraper
from bs4 import BeautifulSoup

from .base_spider import BaseSpider
from .utils import get_default_headers, retry_on_failure


class SPSpider(BaseSpider):
    def __init__(self, conf: str):
        super().__init__(conf)
        self.scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "mobile": False,
            }
        )
        self.scraper.headers.update(get_default_headers())

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_paper_info(self, doi_url: str) -> dict[str, str] | None:
        """
        Extract abstract from IEEE S&P paper page

        Args:
            doi_url: DOI URL of the paper

        Returns:
            Dictionary containing abstract and empty pdf_url if successful, None if failed
        """
        try:
            self.logger.info(f"Fetching paper info from {doi_url}")
            # First request to handle redirect
            response = self.scraper.get(doi_url, allow_redirects=True)
            time.sleep(2)

            # Second request to actual page
            response = self.scraper.get(response.url)

            # Try to extract metadata JSON
            html_text = response.text
            match = re.search(
                r"xplGlobal\.document\.metadata=(\{.*?\});",
                html_text,
                re.DOTALL,
            )

            if match:
                metadata = json.loads(match.group(1))
                if "abstract" in metadata:
                    self.logger.info(
                        "Successfully extracted abstract from metadata"
                    )
                    return {"abstract": metadata["abstract"], "pdf_url": ""}

            # Fallback to HTML parsing
            self.logger.info("Falling back to HTML parsing")
            soup = BeautifulSoup(response.text, "html.parser")
            abstract_div = soup.select_one(
                "div.abstract-text div.u-mb-1 div[xplmathjax]"
            )

            if abstract_div:
                self.logger.info("Successfully extracted abstract from HTML")
                return {
                    "abstract": abstract_div.get_text().strip(),
                    "pdf_url": "",
                }

            self.logger.warning(f"No abstract found for {doi_url}")
            return None

        except Exception as e:
            self.logger.error(f"Error processing {doi_url}: {str(e)}")
            return None


def main():
    spider = SPSpider("sp")
    url = "https://doi.org/10.1109/SP54263.2024.00194"
    result = spider.get_paper_info(url)

    if result:
        print("Abstract:", result["abstract"])
        print("PDF URL:", result["pdf_url"])
    else:
        print("Failed to fetch paper information")


if __name__ == "__main__":
    main()
