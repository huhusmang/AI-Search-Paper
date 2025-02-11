from bs4 import BeautifulSoup

from .base_spider import BaseSpider
from .utils import retry_on_failure, safe_request


class USSSpider(BaseSpider):
    def __init__(self, conf: str):
        super().__init__(conf)
        self.base_url = "https://www.usenix.org"

    @retry_on_failure(max_retries=3, delay=2.0)
    def get_paper_info(self, url: str) -> dict[str, str] | None:
        """
        Extract abstract and PDF URL from a USENIX paper page

        Args:
            url: The paper URL

        Returns:
            Dictionary containing abstract and pdf_url if successful, None if failed
        """
        try:
            self.logger.info(f"Fetching paper info from {url}")
            response = safe_request(url)
            if response.status_code != 200:
                self.logger.error(
                    f"Failed to fetch {url}, status code: {response.status_code}"
                )
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract abstract
            abstract_div = soup.find(
                "div", class_="field-name-field-paper-description"
            )
            if not abstract_div:
                self.logger.warning(f"No abstract found for {url}")
                return None

            abstract_text = (
                abstract_div.find("div", class_="field-item").get_text().strip()
            )

            # Extract PDF URL
            pdf_div = soup.find(
                "div", class_="field-name-field-final-paper-pdf"
            )
            if not pdf_div:
                self.logger.warning(f"No PDF link found for {url}")
                return {"abstract": abstract_text, "pdf_url": ""}

            pdf_url = pdf_div.find("a")["href"]
            if not pdf_url.startswith("http"):
                pdf_url = f"{self.base_url}{pdf_url}"

            self.logger.info(f"Successfully extracted paper info from {url}")
            return {"abstract": abstract_text, "pdf_url": pdf_url}

        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return None


def main():
    spider = USSSpider("uss")
    url = "https://www.usenix.org/conference/usenixsecurity24/presentation/guo-qian"
    result = spider.get_paper_info(url)

    if result:
        print("Abstract:", result["abstract"])
        print("PDF URL:", result["pdf_url"])
    else:
        print("Failed to fetch paper information")


if __name__ == "__main__":
    main()
