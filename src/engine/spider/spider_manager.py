from .base_spider import BaseSpider
from .ccs import CCSSpider
from .ndss import NDSSSpider
from .sp import SPSpider
from .uss import USSSpider


class SpiderManager:
    """Manager class for all paper spiders"""

    # Available spiders mapping
    _spider_classes: dict[str, type[BaseSpider]] = {
        "ccs": CCSSpider,
        "ndss": NDSSSpider,
        "sp": SPSpider,
        "uss": USSSpider,
    }

    def __init__(self, conference: str):
        """
        Initialize spider manager for specific conference

        Args:
            conference: Conference name (ccs/ndss/sp/uss)

        Raises:
            KeyError: If conference not supported
        """
        self.conference = conference.lower()
        if self.conference not in self._spider_classes:
            raise KeyError(f"Conference '{conference}' not supported")

        # Initialize the specific spider
        self.spider = self._spider_classes[self.conference](self.conference)

    def get_paper_info(self, url: str) -> dict[str, str] | None:
        """
        Get paper info using the conference spider

        Args:
            url: Paper URL

        Returns:
            Paper info if successful, None if failed
        """
        return self.spider.get_paper_info(url)


def main():
    # Test cases
    test_cases = [
        ("ccs", "https://doi.org/10.1145/3658644.3690269"),
        (
            "ndss",
            "https://www.ndss-symposium.org/ndss-paper/enhance-stealthiness-and-transferability-of-adversarial-attacks-with-class-activation-mapping-ensemble-attack/",
        ),
        ("sp", "https://doi.org/10.1109/SP54263.2024.00194"),
        (
            "uss",
            "https://www.usenix.org/conference/usenixsecurity24/presentation/guo-qian",
        ),
    ]

    for conference, url in test_cases:
        print(f"\nTesting {conference.upper()} paper: {url}")
        try:
            # Create manager for specific conference
            manager = SpiderManager(conference)
            result = manager.get_paper_info(url)
            if result:
                print("Abstract:", result["abstract"])
                print("PDF URL:", result["pdf_url"])
            else:
                print("Failed to fetch paper information")
        except KeyError as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
