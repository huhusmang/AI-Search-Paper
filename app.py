import streamlit as st

# Must be the first Streamlit command
st.set_page_config(page_title="AI Paper Search", page_icon="📚", layout="wide")

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.search.ai_query import PaperSearchRunner

# Initialize session state
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "is_searching" not in st.session_state:
    st.session_state.is_searching = False
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "current_progress" not in st.session_state:
    st.session_state.current_progress = 0
if "loaded_papers" not in st.session_state:
    st.session_state.loaded_papers = None

# Constants
CONFERENCES = ["ccs", "ndss", "sp", "uss"]
YEARS = [str(year) for year in range(2015, 2025)]
DATA_DIR = Path(__file__).parent / "data"


def load_papers(conference: str, year: str) -> list[dict[str, Any]]:
    """Load papers from the enriched data directory"""
    file_path = DATA_DIR / "enriched" / conference / f"{year}.json"
    if not file_path.exists():
        return []

    with open(file_path) as f:
        papers = json.load(f)
    return [
        p
        for p in papers
        if p.get("info", {}).get("type") == "Conference and Workshop Papers"
    ]


def display_papers(papers: list[dict[str, Any]], show_conference: bool = True):
    """Display papers in a nice format"""
    if not papers:
        return

    # Store papers in session state if they're not from search
    if not st.session_state.search_results:
        st.session_state.loaded_papers = papers

    # Use papers from session state
    papers_to_display = papers

    # Add keyword filter
    all_keywords = set()
    for paper in papers_to_display:
        # Handle both search results and loaded papers
        keywords = paper.get(
            "keywords", paper.get("info", {}).get("keywords", [])
        )
        if isinstance(keywords, str):
            keywords = [keywords]
        all_keywords.update(keywords)

    selected_keyword = st.selectbox(
        "Filter by keyword", ["All"] + sorted(list(all_keywords))
    )

    # Filter papers by keyword if selected
    if selected_keyword != "All":
        papers_to_display = [
            p
            for p in papers_to_display
            if selected_keyword
            in (
                [p.get("keywords", p.get("info", {}).get("keywords"))]
                if isinstance(
                    p.get("keywords", p.get("info", {}).get("keywords")), str
                )
                else p.get("keywords", p.get("info", {}).get("keywords", []))
            )
        ]

    # Display papers
    for paper in papers_to_display:
        # Handle both search results and loaded papers
        info = paper if "title" in paper else paper.get("info", {})
        title = info.get("title", "Untitled")
        if isinstance(title, list):
            title = " ".join(title)

        with st.expander(f"📄 {title}"):
            # Display title inside
            st.markdown(f"### {title}")

            if show_conference:
                st.write(
                    f"**Conference:** {paper.get('conf', 'N/A')} {paper.get('year', 'N/A')}"
                )

            # Authors
            authors = info.get("authors", {}).get("author", [])
            if authors:
                if isinstance(authors, dict):
                    authors = [authors]
                author_names = [
                    author.get("text", author.get("@pid", "Unknown"))
                    for author in authors
                ]
                st.write("**Authors:** " + ", ".join(author_names))

            # Abstract
            abstract = info.get("abstract", paper.get("abstract", "N/A"))
            if isinstance(abstract, list):
                abstract = " ".join(abstract)
            st.write(f"**Abstract:** {abstract}")

            # Keywords and metadata
            keywords = info.get("keywords", paper.get("keywords", []))
            if keywords:
                if isinstance(keywords, str):
                    keywords = [keywords]
                st.write("**Keywords:**")
                cols = st.columns(
                    min(len(keywords), 4)
                )  # Limit to 4 columns max
                for idx, keyword in enumerate(keywords):
                    with cols[idx % 4]:
                        st.markdown(
                            f"<span style='background-color: #f0f2f6; padding: 2px 6px; margin: 0 4px; border-radius: 4px;'>{keyword}</span>",
                            unsafe_allow_html=True,
                        )

            # Paper link
            if "url" in paper:
                url = paper["url"]
            elif "ee" in info:
                url = info["ee"]
                if isinstance(url, list):
                    url = url[0]
            else:
                url = None

            if url:
                st.markdown(f"[📄 View Paper]({url})")


def search_papers(query: str, conference: str = None, year: str = None):
    """Search papers using AI query with progress tracking"""
    ai_query = PaperSearchRunner(
        query=query,
        conference=conference,
        years=year,
    )
    results = ai_query.run()

    # Reset progress
    st.session_state.current_progress = 0

    # Add to search history
    st.session_state.search_history.append(
        {
            "query": query,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "conference": conference,
            "year": year,
        }
    )

    return results if results else []  # Ensure we always return a list


# UI Layout
st.title("AI Paper Search 📚")
st.write("Search and explore academic papers from top security conferences")

# Tabs for different features
tab1, tab2, tab3 = st.tabs(
    ["Browse Papers 📋", "AI Search 🔍", "Search History 📜"]
)

with tab1:
    st.header("Browse Papers")
    col1, col2 = st.columns(2)

    with col1:
        conference = st.selectbox("Select Conference", CONFERENCES)
    with col2:
        year = st.selectbox("Select Year", YEARS)

    if st.button("Load Papers"):
        with st.spinner("Loading papers..."):
            papers = load_papers(conference, year)
            if papers:
                st.session_state.loaded_papers = papers
                st.success(f"Found {len(papers)} papers")
                display_papers(papers, show_conference=False)
            else:
                st.info(f"No papers found for {conference} {year}")
    elif st.session_state.loaded_papers:
        display_papers(st.session_state.loaded_papers, show_conference=False)

with tab2:
    st.header("AI-Powered Search")

    # Search filters
    col1, col2 = st.columns(2)
    with col1:
        search_conf = st.selectbox(
            "Filter by Conference (Optional)", ["All"] + CONFERENCES
        )
    with col2:
        search_year = st.selectbox("Filter by Year (Optional)", ["All"] + YEARS)

    # Search query
    query = st.text_area(
        "Enter your search query",
        help="Describe what you're looking for in natural language. The AI will find relevant papers.",
    )

    if st.button("Search", type="primary"):
        if not query:
            st.warning("Please enter a search query")
        else:
            st.session_state.is_searching = True

            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                status_text.text("Initializing search...")
                progress_bar.progress(10)

                conf = None if search_conf == "All" else search_conf
                year = None if search_year == "All" else search_year

                status_text.text(
                    "Searching papers using AI... This may take a few minutes."
                )
                progress_bar.progress(30)

                results = search_papers(query, conference=conf, year=year)
                progress_bar.progress(90)

                if results and len(results) > 0:
                    st.session_state.search_results = results
                    progress_bar.progress(100)
                    status_text.empty()

                    st.success(f"Found {len(results)} relevant papers")
                    display_papers(results)
                else:
                    st.session_state.search_results = None
                    progress_bar.progress(100)
                    status_text.empty()
                    st.info("No relevant papers found")

            except Exception as e:
                st.error(f"An error occurred during search: {str(e)}")
            finally:
                st.session_state.is_searching = False

with tab3:
    st.header("Search History")
    if st.session_state.search_history:
        for i, search in enumerate(reversed(st.session_state.search_history)):
            with st.expander(
                f"🔍 {search['query'][:50]}... ({search['timestamp']})"
            ):
                st.write(f"**Query:** {search['query']}")
                st.write(f"**Time:** {search['timestamp']}")
                if search["conference"]:
                    st.write(f"**Conference:** {search['conference']}")
                if search["year"]:
                    st.write(f"**Year:** {search['year']}")

                # Add button to rerun the search
                if st.button("🔄 Rerun Search", key=f"rerun_{i}"):
                    # Switch to search tab
                    st.session_state.search_results = None
                    st.experimental_set_query_params(tab="AI Search")
                    # Set the search parameters
                    st.session_state["query"] = search["query"]
                    st.session_state["conference"] = search["conference"]
                    st.session_state["year"] = search["year"]
                    st.experimental_rerun()
    else:
        st.info("No search history yet. Try searching for some papers!")
