import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path


class BaseSpider(ABC):
    """Base spider class for paper abstract extraction"""

    def __init__(self, conf: str):
        """
        Initialize base spider with common attributes

        Args:
            conf: name for logging
        """
        self.name = self.__class__.__name__
        self._setup_logger(conf)

    def _setup_logger(self, conf: str) -> None:
        """
        Setup logger for the spider

        Args:
            conf: name for log file
        """
        # Create logger
        self.logger = logging.getLogger(f"spider.{self.name}")
        self.logger.setLevel(logging.INFO)

        # 如果已经有处理器，说明已经配置过，直接返回
        if self.logger.handlers:
            return

        # Create formatters
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        # Create and configure file handler
        log_dir = Path("log/spider") / conf
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(
            log_dir / f"{self.name.lower()}.log", encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)

        # Create and configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    @abstractmethod
    def get_paper_info(self, url: str) -> dict[str, str] | None:
        """
        Extract paper information from the given URL

        Args:
            url: URL of the paper page

        Returns:
            Dictionary containing:
            - 'abstract': paper abstract
            - 'pdf_url': URL to PDF file (empty string if not available)
            Returns None if extraction fails
        """
        pass
