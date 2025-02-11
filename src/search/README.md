# AI Search Module

This module is designed to facilitate semantic search and keyword extraction from research papers. It leverages language models to assess the relevance of papers based on user queries and to extract meaningful keywords from paper titles and abstracts.

## Structure

- **`ai_query.py`**: Contains the `PaperSemanticSearch` class, which implements methods for loading datasets, filtering papers, checking relevance using language models, and managing cache and output directories.
- **`label.py`**: Includes the `KeywordExtractor` class, which processes papers to extract keywords using language models and handles caching of results.
- **`config.py`**: Defines configuration classes for model parameters and API keys.
- **`utils.py`**: Provides utility functions such as `call_llm` for interacting with language models.

## Key Classes and Functions

- **`PaperSemanticSearch`**:
  - `__init__`: Initializes the search engine with directories for enriched data and cache, and sets up the dataset.
  - `_check_relevance`: Uses a language model to determine the relevance of a paper to a given query.

- **`KeywordExtractor`**:
  - `__init__`: Sets up directories for enriched data and cache.
  - `_extract_keywords`: Extracts keywords from paper titles and abstracts using language models.

- **`call_llm`**: A utility function in `utils.py` for making API calls to language models.

## Usage

1. **Setup**: Ensure that the necessary API keys are set in `config.py`.
2. **Running Searches**: Use the `PaperSemanticSearch` class to perform semantic searches on AI papers.
3. **Keyword Extraction**: Utilize the `KeywordExtractor` class to extract keywords from paper datasets.
