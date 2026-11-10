"""
Valkey Search 1.3 Demo - Streamlit Web UI

A shopping app demo showcasing valkey-search 1.3 features:
- Multi-language FTS
- BM25STD Scoring
- Vector Search (BFLOAT16 + Range)
- FT.HYBRID Search
- Cursor Pagination

Run with: streamlit run app.py
"""

import time
from collections import deque
from dataclasses import dataclass, field

import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Valkey Search 1.3 Demo",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# Latency Tracking
# -----------------------------------------------------------------------------
@dataclass
class LatencyTracker:
    """Track query latencies for the meter display."""
    history: deque = field(default_factory=lambda: deque(maxlen=50))
    last_latency_ms: float = 0.0
    
    def record(self, latency_ms: float):
        self.history.append(latency_ms)
        self.last_latency_ms = latency_ms
    
    @property
    def avg_latency_ms(self) -> float:
        if not self.history:
            return 0.0
        return sum(self.history) / len(self.history)
    
    @property
    def p99_latency_ms(self) -> float:
        if not self.history:
            return 0.0
        sorted_latencies = sorted(self.history)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]


# Initialize session state
if "latency_tracker" not in st.session_state:
    st.session_state.latency_tracker = LatencyTracker()
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "connected" not in st.session_state:
    st.session_state.connected = False
if "client" not in st.session_state:
    st.session_state.client = None


# -----------------------------------------------------------------------------
# Valkey Connection
# -----------------------------------------------------------------------------
def get_client():
    """Get or create Valkey client."""
    if st.session_state.client is None:
        try:
            from core.client import get_client as create_client
            st.session_state.client = create_client()
            st.session_state.connected = True
        except Exception as e:
            st.session_state.connected = False
            st.error(f"Failed to connect to Valkey: {e}")
            return None
    return st.session_state.client


def timed_search(client, *args) -> tuple[list, float]:
    """Execute a search and return (results, latency_ms)."""
    start = time.perf_counter()
    results = client.execute_command("FT.SEARCH", *args)
    latency_ms = (time.perf_counter() - start) * 1000
    st.session_state.latency_tracker.record(latency_ms)
    return results, latency_ms


# -----------------------------------------------------------------------------
# UI Components
# -----------------------------------------------------------------------------
def render_latency_meter():
    """
    Render a visual latency meter.
    
    Shows:
    - Current latency as a large number
    - Color-coded gauge (green < 1ms, yellow < 10ms, red > 10ms)
    - Rolling average and P99
    """
    tracker = st.session_state.latency_tracker
    latency = tracker.last_latency_ms
    
    # Determine color based on latency thresholds
    if latency < 1:
        color = "#22c55e"  # green
        status = "⚡ Blazing"
    elif latency < 5:
        color = "#84cc16"  # lime
        status = "✓ Fast"
    elif latency < 10:
        color = "#eab308"  # yellow
        status = "● Normal"
    elif latency < 50:
        color = "#f97316"  # orange
        status = "◐ Slow"
    else:
        color = "#ef4444"  # red
        status = "⚠ Very Slow"
    
    # SVG gauge
    # Arc from -135° to 135° (270° total sweep)
    # Latency 0-100ms maps to this arc
    max_latency = 100  # ms for full gauge
    angle = min(latency / max_latency, 1.0) * 270 - 135
    
    gauge_svg = f'''
    <svg viewBox="0 0 200 120" style="width: 100%; max-width: 300px;">
        <!-- Background arc -->
        <path d="M 20 100 A 80 80 0 1 1 180 100" 
              fill="none" stroke="#e5e7eb" stroke-width="12" stroke-linecap="round"/>
        
        <!-- Color zones -->
        <path d="M 20 100 A 80 80 0 0 1 58 32" 
              fill="none" stroke="#22c55e" stroke-width="12" stroke-linecap="round" opacity="0.3"/>
        <path d="M 58 32 A 80 80 0 0 1 100 20" 
              fill="none" stroke="#eab308" stroke-width="12" opacity="0.3"/>
        <path d="M 100 20 A 80 80 0 0 1 180 100" 
              fill="none" stroke="#ef4444" stroke-width="12" stroke-linecap="round" opacity="0.3"/>
        
        <!-- Needle -->
        <line x1="100" y1="100" x2="100" y2="35" 
              stroke="{color}" stroke-width="4" stroke-linecap="round"
              transform="rotate({angle}, 100, 100)"/>
        
        <!-- Center dot -->
        <circle cx="100" cy="100" r="8" fill="{color}"/>
        
        <!-- Labels -->
        <text x="25" y="115" font-size="10" fill="#6b7280">0</text>
        <text x="95" y="12" font-size="10" fill="#6b7280">50</text>
        <text x="170" y="115" font-size="10" fill="#6b7280">100ms</text>
    </svg>
    '''
    
    st.markdown(gauge_svg, unsafe_allow_html=True)
    
    # Stats row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Last Query", f"{latency:.2f} ms", status)
    with col2:
        st.metric("Avg (last 50)", f"{tracker.avg_latency_ms:.2f} ms")
    with col3:
        st.metric("P99", f"{tracker.p99_latency_ms:.2f} ms")


def render_search_results(results: list, latency_ms: float):
    """Render search results in a nice card format."""
    if not results or results[0] == 0:
        st.info("No results found")
        return
    
    total = results[0]
    st.caption(f"Found {total} results in {latency_ms:.2f}ms")
    
    # Parse and display results
    i = 1
    while i < len(results):
        key = results[i]
        fields = results[i + 1] if i + 1 < len(results) else []
        
        # Convert to dict
        item = {}
        for j in range(0, len(fields), 2):
            item[fields[j]] = fields[j + 1]
        
        # Card display
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{item.get('title', key)}**")
                if desc := item.get('description'):
                    st.caption(desc[:150] + "..." if len(desc) > 150 else desc)
                if cat := item.get('category'):
                    tags = cat.replace("|", " · ")
                    st.markdown(f"<small style='color: #6b7280;'>{tags}</small>", unsafe_allow_html=True)
            with col2:
                if price := item.get('price'):
                    st.markdown(f"### ${price}")
                if rating := item.get('rating'):
                    st.markdown(f"⭐ {rating}")
            st.divider()
        
        i += 2


# -----------------------------------------------------------------------------
# Feature Pages
# -----------------------------------------------------------------------------
def page_home():
    """Home page with feature overview."""
    st.title("🔍 Valkey Search 1.3 Demo")
    st.markdown("### Shopping App - Feature Showcase")
    
    st.markdown("""
    This demo showcases the new features in **valkey-search 1.3**:
    
    | Feature | What's New |
    |---------|-----------|
    | 🌍 Multi-language FTS | 12 Snowball stemmer languages |
    | 📊 BM25STD Scoring | Relevance-ranked results with WITHSCORES |
    | 🧠 Vector Search | FLOAT16/BFLOAT16 types + Range queries |
    | 🔀 FT.HYBRID | Text + Vector fusion (RRF/LINEAR) |
    | 📄 Cursors | Paginated results with WITHCURSOR |
    
    👈 **Select a feature from the sidebar** to try it out!
    """)
    
    # Connection status
    client = get_client()
    if client:
        st.success("✓ Connected to Valkey")
        # Show module info
        try:
            modules = client.execute_command("MODULE", "LIST")
            for mod in modules:
                if b"search" in mod or "search" in str(mod):
                    st.caption(f"Module: {mod}")
        except:
            pass
    else:
        st.warning("⚠ Not connected to Valkey. Start the server first.")


def page_multilang():
    """Multi-language FTS demo page."""
    st.title("🌍 Multi-Language Full-Text Search")
    st.markdown("Search products in different languages with proper stemming.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        language = st.selectbox(
            "Store Language",
            ["English", "German", "French", "Spanish"],
            help="Each language uses its own Snowball stemmer"
        )
        
        # Default queries per language
        default_queries = {
            "English": "running shoes waterproof",
            "German": "Laufschuhe wasserdicht",
            "French": "chaussures imperméables",
            "Spanish": "zapatos impermeables",
        }
        
        query = st.text_input("Search products", value=default_queries[language])
        search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
    
    with col2:
        st.markdown("### Latency")
        render_latency_meter()
    
    if search_btn and query:
        client = get_client()
        if client:
            # Map language to index
            index_map = {
                "English": "products_idx",
                "German": "products_de_idx", 
                "French": "products_fr_idx",
                "Spanish": "products_es_idx",
            }
            index = index_map[language]
            
            results, latency = timed_search(
                client, index, query,
                "RETURN", "4", "title", "description", "price", "category"
            )
            render_search_results(results, latency)


def page_bm25():
    """BM25 scoring demo page."""
    st.title("📊 BM25STD Text Scoring")
    st.markdown("See relevance scores for each result.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        query = st.text_input("Search query", value="wireless bluetooth headphones")
        
        scorer = st.radio(
            "Scorer",
            ["BM25STD", "Default"],
            horizontal=True,
            help="BM25STD is the new industry-standard scorer in 1.3"
        )
        
        search_btn = st.button("🔍 Search with Scores", type="primary")
    
    with col2:
        st.markdown("### Latency")
        render_latency_meter()
    
    if search_btn and query:
        client = get_client()
        if client:
            args = ["products_idx", query, "WITHSCORES"]
            if scorer == "BM25STD":
                args.extend(["SCORER", "BM25STD"])
            args.extend(["RETURN", "3", "title", "price", "description"])
            
            start = time.perf_counter()
            results = client.execute_command("FT.SEARCH", *args)
            latency = (time.perf_counter() - start) * 1000
            st.session_state.latency_tracker.record(latency)
            
            if results and results[0] > 0:
                st.caption(f"Found {results[0]} results in {latency:.2f}ms")
                
                # Parse with scores
                i = 1
                while i < len(results):
                    key = results[i]
                    score = float(results[i + 1]) if i + 1 < len(results) else 0
                    fields = results[i + 2] if i + 2 < len(results) else []
                    
                    item = dict(zip(fields[::2], fields[1::2]))
                    
                    # Visual score bar
                    bar_pct = min(score * 100, 100) if score <= 1 else min(score * 10, 100)
                    
                    with st.container():
                        st.markdown(f"**{item.get('title', key)}**")
                        st.progress(bar_pct / 100, text=f"Relevance: {score:.4f}")
                        if price := item.get('price'):
                            st.caption(f"${price}")
                        st.divider()
                    
                    i += 3
            else:
                st.info("No results found")


def page_vector():
    """Vector search demo page."""
    st.title("🧠 Vector Search")
    st.markdown("Semantic search with BFLOAT16 vectors and range queries.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_type = st.radio(
            "Search Type",
            ["KNN (Top K)", "Range (Similarity Threshold)"],
            horizontal=True
        )
        
        query = st.text_input(
            "Semantic query",
            value="comfortable shoes for standing all day",
            help="Describe what you're looking for in natural language"
        )
        
        if search_type == "KNN (Top K)":
            k = st.slider("Number of results (K)", 1, 20, 5)
        else:
            threshold = st.slider("Similarity threshold", 0.5, 0.95, 0.7, 0.05)
        
        search_btn = st.button("🔍 Semantic Search", type="primary")
    
    with col2:
        st.markdown("### Latency")
        render_latency_meter()
        
        st.markdown("---")
        st.markdown("### Memory Savings")
        st.markdown("""
        | Type | Size |
        |------|------|
        | FLOAT32 | 1536 bytes |
        | **BFLOAT16** | **768 bytes** |
        
        **50% reduction!**
        """)
    
    if search_btn and query:
        client = get_client()
        if client:
            # Generate embedding
            try:
                from sentence_transformers import SentenceTransformer
                from core.data_loader import DataLoader
                
                with st.spinner("Generating embedding..."):
                    model = SentenceTransformer("all-MiniLM-L6-v2")
                    embedding = model.encode(query)
                    query_vec = DataLoader._vector_to_bytes(embedding, "bfloat16")
                
                if search_type == "KNN (Top K)":
                    results, latency = timed_search(
                        client, "products_idx",
                        f"(*)=>[KNN {k} @embedding $query_vec]",
                        "PARAMS", "2", "query_vec", query_vec,
                        "RETURN", "3", "title", "price", "category",
                        "DIALECT", "2"
                    )
                else:
                    radius = 1 - threshold
                    results, latency = timed_search(
                        client, "products_idx",
                        f"(*)=>[VECTOR_RANGE {radius} @embedding $query_vec]",
                        "PARAMS", "2", "query_vec", query_vec,
                        "RETURN", "3", "title", "price", "category",
                        "DIALECT", "2"
                    )
                
                render_search_results(results, latency)
                
            except ImportError:
                st.error("sentence-transformers not installed. Run: pip install sentence-transformers")


def page_hybrid():
    """Hybrid search demo page."""
    st.title("🔀 FT.HYBRID Search")
    st.markdown("Combine keyword matching with semantic similarity.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        query = st.text_input(
            "Search query",
            value="noise cancelling for focus work",
            help="Keywords + semantic meaning combined"
        )
        
        fusion = st.radio(
            "Fusion Method",
            ["RRF (Reciprocal Rank Fusion)", "LINEAR (Weighted)"],
            horizontal=True
        )
        
        if "LINEAR" in fusion:
            st.markdown("##### Weights")
            text_weight = st.slider("Text weight", 0.0, 1.0, 0.3, 0.1)
            vector_weight = 1.0 - text_weight
            st.caption(f"Vector weight: {vector_weight:.1f}")
        
        search_btn = st.button("🔍 Hybrid Search", type="primary")
    
    with col2:
        st.markdown("### Latency")
        render_latency_meter()
    
    if search_btn and query:
        client = get_client()
        if client:
            try:
                from sentence_transformers import SentenceTransformer
                from core.data_loader import DataLoader
                
                with st.spinner("Running hybrid search..."):
                    model = SentenceTransformer("all-MiniLM-L6-v2")
                    embedding = model.encode(query)
                    query_vec = DataLoader._vector_to_bytes(embedding, "bfloat16")
                    
                    args = [
                        "products_idx",
                        "TEXT", query,
                        "VECTOR", "KNN", "5", "@embedding", "query_vec",
                    ]
                    
                    if "RRF" in fusion:
                        args.extend(["FUSION", "RRF"])
                    else:
                        args.extend(["FUSION", "LINEAR", str(text_weight), str(vector_weight)])
                    
                    args.extend([
                        "PARAMS", "2", "query_vec", query_vec,
                        "RETURN", "3", "title", "price", "category",
                        "LIMIT", "0", "5"
                    ])
                    
                    start = time.perf_counter()
                    results = client.execute_command("FT.HYBRID", *args)
                    latency = (time.perf_counter() - start) * 1000
                    st.session_state.latency_tracker.record(latency)
                    
                    render_search_results(results, latency)
                    
            except ImportError:
                st.error("sentence-transformers not installed")


def page_cursor():
    """Cursor pagination demo page."""
    st.title("📄 Cursor Pagination")
    st.markdown("Browse large result sets without re-running the query.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        query = st.text_input("Search query", value="*", help="Use * to browse all products")
        page_size = st.slider("Results per page", 2, 10, 3)
        
        if st.button("🔍 Start Browsing", type="primary"):
            client = get_client()
            if client:
                results, latency = timed_search(
                    client, "products_idx", query,
                    "WITHCURSOR", "COUNT", str(page_size),
                    "RETURN", "3", "title", "price", "category"
                )
                
                if results and len(results) >= 2:
                    st.session_state.cursor_results = results[0]
                    st.session_state.cursor_id = results[1]
                    st.session_state.cursor_page = 1
        
        # Show current page
        if "cursor_results" in st.session_state:
            st.markdown(f"### Page {st.session_state.get('cursor_page', 1)}")
            
            cursor_results = st.session_state.cursor_results
            if cursor_results and cursor_results[0] > 0:
                render_search_results(cursor_results, 0)
            
            # Load more button
            if st.session_state.get("cursor_id"):
                if st.button("Load More →"):
                    client = get_client()
                    if client:
                        start = time.perf_counter()
                        results = client.execute_command(
                            "FT.CURSOR", "READ",
                            "products_idx",
                            st.session_state.cursor_id,
                            "COUNT", str(page_size)
                        )
                        latency = (time.perf_counter() - start) * 1000
                        st.session_state.latency_tracker.record(latency)
                        
                        if results and len(results) >= 2:
                            st.session_state.cursor_results = results[0]
                            st.session_state.cursor_id = results[1] if results[1] != 0 else None
                            st.session_state.cursor_page += 1
                            st.rerun()
            else:
                st.info("End of results")
    
    with col2:
        st.markdown("### Latency")
        render_latency_meter()


# -----------------------------------------------------------------------------
# Main App
# -----------------------------------------------------------------------------
def main():
    # Sidebar navigation
    st.sidebar.title("Valkey Search 1.3")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Features",
        [
            "🏠 Home",
            "🌍 Multi-language FTS",
            "📊 BM25 Scoring",
            "🧠 Vector Search",
            "🔀 Hybrid Search",
            "📄 Cursor Pagination",
        ]
    )
    
    # Connection status in sidebar
    st.sidebar.markdown("---")
    if st.session_state.connected:
        st.sidebar.success("✓ Connected")
    else:
        st.sidebar.warning("⚠ Disconnected")
        if st.sidebar.button("Connect"):
            get_client()
            st.rerun()
    
    # Route to page
    if page == "🏠 Home":
        page_home()
    elif page == "🌍 Multi-language FTS":
        page_multilang()
    elif page == "📊 BM25 Scoring":
        page_bm25()
    elif page == "🧠 Vector Search":
        page_vector()
    elif page == "🔀 Hybrid Search":
        page_hybrid()
    elif page == "📄 Cursor Pagination":
        page_cursor()


if __name__ == "__main__":
    main()
