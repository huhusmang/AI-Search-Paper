# Engine Module

## Overview
The `src/engine` directory contains modules for fetching and processing academic paper information from various conferences.

## Modules
- **dblp.py**: Fetches and processes conference papers from DBLP.
- **sema.py**: Fetches and processes conference papers from Semantic Scholar.
- **enrich.py**: Enriches DBLP data with additional information from Semantic Scholar.
- **enrich_missing.py**: Updates missing abstracts in enriched data.
- **stats.py**: Analyzes and summarizes data, particularly focusing on abstract availability.

## Spider Manager
The `spider` subdirectory contains specialized spiders for different conferences:
- `CCSSpider`, `NDSSpider`, `SPSpider`, and `USSSpider`.
- **spider_manager.py**: Manages the initialization and operation of these spiders based on the specified conference.

## Usage
1. run `dblp.py` to fetch DBLP data.
2. run `sema.py` to fetch Semantic Scholar data.
3. run `enrich.py` to enrich DBLP data with Semantic Scholar information.
   
4. run `stats.py` to analyze and summarize data.
5. run `enrich_missing.py` to update missing abstracts in enriched data.