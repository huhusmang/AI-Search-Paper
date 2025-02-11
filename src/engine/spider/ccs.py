import random
import re
import time

import requests
from bs4 import BeautifulSoup

from .base_spider import BaseSpider
from .utils import retry_on_failure


class CCSSpider(BaseSpider):
    def __init__(self, conf: str):
        super().__init__(conf)
        # Add custom headers to mimic a real browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        # Add session to maintain cookies
        self.session = requests.Session()

    @retry_on_failure(max_retries=3, delay=6.0)
    def get_paper_info(self, url: str) -> dict[str, str] | None:
        """
        Extract abstract from a CCS paper given its DOI URL

        Args:
            url: DOI URL of the paper

        Returns:
            Dictionary containing abstract and empty pdf_url if successful, None if failed
        """
        try:
            self.logger.info(f"Fetching paper info from {url}")

            # Convert DOI URL to ACM DL URL if needed
            if url.startswith("https://doi.org/"):
                acm_url = url.replace(
                    "https://doi.org/", "https://dl.acm.org/doi/"
                )
            else:
                acm_url = url

            # Add random delay between requests
            time.sleep(random.uniform(2, 5))

            # Use session with custom headers
            response = self.session.get(
                acm_url, headers=self.headers, timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the abstract section
            abstract_div = soup.find("div", {"id": "abstracts"})
            if not abstract_div:
                self.logger.warning(f"No abstract section found for {url}")
                return None

            # Get the abstract text
            abstract_text = abstract_div.find("div", {"role": "paragraph"})
            if not abstract_text:
                self.logger.warning(f"No abstract text found for {url}")
                return None

            # Clean up the text
            text = abstract_text.get_text(strip=True)
            text = re.sub(r"\s+", " ", text)

            self.logger.info(f"Successfully extracted abstract from {url}")
            return {"abstract": text, "pdf_url": ""}

        except requests.RequestException as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error processing {url}: {str(e)}")
            return None


def main():
    spider = CCSSpider("ccs")
    url = "https://doi.org/10.1145/3658644.3690269"
    result = spider.get_paper_info(url)

    if result:
        print("Abstract:", result["abstract"])
        print("PDF URL:", result["pdf_url"])
    else:
        print("Failed to fetch paper information")


if __name__ == "__main__":
    main()
