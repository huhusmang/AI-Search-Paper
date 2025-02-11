import requests
from bs4 import BeautifulSoup

from .base_spider import BaseSpider
from .utils import get_default_headers, retry_on_failure


class NDSSSpider(BaseSpider):
    def __init__(self, conf: str):
        super().__init__(conf)
        self.base_url = "https://www.ndss-symposium.org"
        self.headers = get_default_headers()

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_paper_info(self, paper_url: str) -> dict[str, str] | None:
        """
        Extract abstract and PDF URL from paper page

        Args:
            paper_url: Paper page URL

        Returns:
            Dictionary containing 'abstract' and 'pdf_url' if successful, None otherwise
        """
        try:
            self.logger.info(f"Fetching paper info from {paper_url}")
            response = requests.get(paper_url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Try the first format (paper-data class)
            paper_data = soup.find("div", {"class": "paper-data"})
            if paper_data:
                paragraphs = paper_data.find_all("p")
                abstract_text = (
                    paragraphs[2].text.strip() if len(paragraphs) >= 3 else None
                )
                pdf_button = soup.find("a", {"class": "pdf-button"})
                pdf_url = pdf_button["href"] if pdf_button else None
            else:
                # Try the second format (new-wrapper class)
                new_wrapper = soup.find("section", {"class": "new-wrapper"})
                if new_wrapper:
                    # Find abstract - it's the paragraph after the "Abstract:" heading
                    abstract_heading = new_wrapper.find(
                        "h2", string="Abstract:"
                    )
                    if abstract_heading:
                        abstract_text = abstract_heading.find_next(
                            "p"
                        ).text.strip()
                    else:
                        abstract_text = None

                    # Find PDF URL - look for a link containing "Paper" text
                    pdf_link = new_wrapper.find("a", string="Paper")
                    pdf_url = pdf_link["href"] if pdf_link else None
                else:
                    self.logger.warning(
                        f"No recognized format found for {paper_url}"
                    )
                    return None

            if not abstract_text or not pdf_url:
                self.logger.warning(
                    f"Failed to extract complete information from {paper_url}"
                )
                return None

            # Make sure PDF URL is absolute
            if pdf_url.startswith("/"):
                pdf_url = self.base_url + pdf_url

            self.logger.info(
                f"Successfully extracted paper info from {paper_url}"
            )
            return {"abstract": abstract_text, "pdf_url": pdf_url}

        except Exception as e:
            self.logger.error(
                f"Error fetching paper info from {paper_url}: {str(e)}"
            )
            return None


def main():
    spider = NDSSSpider("ndss")
    url = "https://www.ndss-symposium.org/ndss-paper/enhance-stealthiness-and-transferability-of-adversarial-attacks-with-class-activation-mapping-ensemble-attack/"
    result = spider.get_paper_info(url)

    if result:
        print("Abstract:", result["abstract"])
        print("PDF URL:", result["pdf_url"])
    else:
        print("Failed to fetch paper information")


if __name__ == "__main__":
    main()
