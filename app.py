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

import numpy as np
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


SHOP_INDEX = "shop_idx"
SHOP_PREFIX = "shop:"
SHOP_CREATE_ARGS = [
    SHOP_INDEX, "ON", "HASH", "PREFIX", "1", SHOP_PREFIX, "SCORE_FIELD", "quality", "SCHEMA",
    "title", "TEXT", "description", "TEXT", "category", "TAG", "price", "NUMERIC", "quality", "NUMERIC",
    "embedding", "VECTOR", "HNSW", "6", "TYPE", "FLOAT32", "DIM", "384", "DISTANCE_METRIC", "COSINE",
]
# Every product has the same quality, so the steps show pure BM25 effects.
SHOP_QUALITY = 1.0

# Tuned so each step shows its effect: e.g. the keyword-stuffed listing (#3) must
# lose to the focused one on "running shoes", and the waterproof shoes must rank
# last on plain "shoes" so the boost visibly lifts them. Descriptions say "running",
# not "run": "run" is indexed as a separate, rarer term and skews scores. Re-check if you edit.
SHOP_PRODUCTS = [
    ("Running Shoes", "Lightweight running shoes for everyday running.", "shoes", 45),
    ("Trail Running Shoes", "Grippy trail running shoes built for rocky mountain paths.", "shoes", 95),
    ("Running Shoes Sneakers Trainers - Men Women Kids - Best Cheap Sale",
     "running shoes running sneakers running trainers jogging shoes walking shoes gym shoes tennis shoes "
     "sports shoes casual shoes marathon running shoes best running shoes cheap shoes discount shoes "
     "sale shoes free shipping new arrival hot deal top rated shoes buy now limited offer men women kids all "
     "sizes all colors great for gym workouts walking travel school office weekend parties summer winter "
     "spring autumn style comfort value quality guaranteed fast delivery easy returns gift idea", "shoes", 29),
    ("Waterproof Hiking Shoes",
     "Sturdy waterproof hiking shoes with a sealed membrane, ankle support and a deep lug outsole "
     "for wet, muddy trails.", "shoes", 120),
    ("Rain-Ready Trail Shoes",
     "Waterproof trail shoes with a breathable lining that keep your feet dry through puddles "
     "and heavy rain.", "shoes", 110),
    ("Leather Dress Shoes", "Classic leather dress shoes for the office.", "shoes", 150),
    ("Canvas Slip-On Shoes", "Casual canvas shoes for everyday wear.", "shoes", 39),
    ("Waterproof Rain Jacket", "Packable waterproof jacket with sealed seams.", "apparel", 80),
    ("Running Jacket", "Windproof jacket for running in cold weather.", "apparel", 70),
    ("Down Jacket", "Warm insulated down jacket for winter.", "apparel", 160),
    ("Running Socks (3-Pack)", "Cushioned moisture-wicking socks for running.", "apparel", 15),
    ("Running Shorts", "Breathable running shorts with a zip pocket.", "apparel", 30),
    ("GPS Running Watch", "Tracks pace, distance and heart rate on every workout.", "electronics", 199),
    ("Wireless Earbuds", "Sweat-resistant earbuds that stay put during workouts.", "electronics", 89),
    ("Insulated Water Bottle", "Keeps drinks cold for 24 hours.", "kitchen", 25),
    ("Yoga Mat", "Non-slip mat for yoga and pilates.", "fitness", 40),
    ("Foam Roller", "Firm foam roller for stretching and muscle recovery after running or the gym.",
     "fitness", 30),
    ("Hiking Backpack", "Lightweight backpack with padded straps.", "outdoor", 85),
    ("Camping Tent", "Two-person tent for weekend trips.", "outdoor", 210),
    ("Wool Beanie", "Soft knit beanie for cold mornings.", "apparel", 20),
]


@st.cache_resource
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed(text: str) -> bytes:
    return np.asarray(get_embedder().encode(text), dtype=np.float32).tobytes()


def shop_index_docs(client) -> int | None:
    """Return num_docs of the shop index, or None if it doesn't exist."""
    if SHOP_INDEX not in client.execute_command("FT._LIST"):
        return None
    info = client.execute_command("FT.INFO", SHOP_INDEX)
    return int(dict(zip(info[::2], info[1::2])).get("num_docs", 0))


def setup_shop_index(client) -> None:
    if SHOP_INDEX in client.execute_command("FT._LIST"):
        client.execute_command("FT.DROPINDEX", SHOP_INDEX)
    for key in client.scan_iter(f"{SHOP_PREFIX}*"):
        client.delete(key)
    client.execute_command("FT.CREATE", *SHOP_CREATE_ARGS)
    for i, (title, desc, category, price) in enumerate(SHOP_PRODUCTS, 1):
        client.hset(f"{SHOP_PREFIX}{i:02d}", mapping={
            "title": title, "description": desc, "category": category, "price": price,
            "quality": SHOP_QUALITY, "embedding": embed(f"{title}. {desc}"),
        })


def shop_search(client, query: str, *extra) -> list[dict]:
    """FT.SEARCH with WITHSCORES on the shop index; returns rows for display."""
    results, _ = timed_search(
        client, SHOP_INDEX, query, "WITHSCORES",
        # Everything except the raw embedding bytes.
        "RETURN", "6", "title", "description", "category", "price", "quality", "__embedding_score",
        *extra,
    )
    rows = []
    for i in range(1, len(results), 3):
        fields = dict(zip(results[i + 2][::2], results[i + 2][1::2]))
        rows.append({"key": results[i], "score": results[i + 1], **fields})
    return rows


def show_shop_query(client, query: str, *extra) -> None:
    """Show the FT.SEARCH command and its scored results."""
    shown = " ".join("$v" if isinstance(a, bytes) else str(a) for a in extra)
    st.code(f"FT.SEARCH {SHOP_INDEX} '{query}' WITHSCORES {shown}".rstrip(), language=None)
    try:
        rows = shop_search(client, query, *extra)
    except Exception as e:
        st.error(str(e))
        return
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("No results")


def form_submitted(form_key: str, clicked: bool) -> bool:
    """True once the form has been submitted, so results persist across reruns."""
    if clicked:
        st.session_state[f"{form_key}_submitted"] = True
    return st.session_state.get(f"{form_key}_submitted", False)


def page_bm25():
    """BM25 scoring demo page: a shopping site walkthrough on its own index."""
    st.title("📊 BM25STD Text Scoring")
    st.markdown(
        "A shopping-site walkthrough of BM25STD, the 1.3 text scorer (and the default). "
        "Every query uses `WITHSCORES` so you can see why results rank the way they do."
    )

    client = get_client()
    if not client:
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### ① Setup")
        st.code("FT.CREATE " + " ".join(SHOP_CREATE_ARGS).replace(" SCHEMA ", " SCHEMA\n  "), language=None)
        st.caption(
            "`SCORE_FIELD quality` multiplies each product's BM25 score by its `quality` value. "
            f"All products use quality = {SHOP_QUALITY} here, so the steps below show pure BM25."
        )
        with st.expander(f"Product catalog ({len(SHOP_PRODUCTS)} items)"):
            st.dataframe(
                [{"Title": t, "Description": d, "Category": c, "Price": f"${p}"} for t, d, c, p in SHOP_PRODUCTS],
                hide_index=True, width="stretch",
            )
        if st.button("Create index & load products", type="primary"):
            with st.spinner("Creating shop_idx and embedding products..."):
                setup_shop_index(client)
        num_docs = shop_index_docs(client)
        if num_docs is None:
            st.warning("`shop_idx` doesn't exist yet. Click the button above to create it.")
            return
        st.success(f"`shop_idx` ready: {num_docs} products indexed")
    with col2:
        st.markdown("### Latency")
        latency_slot = st.container()

    tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["② Relevance", "③ Boost", "④ Smart matching", "⑤ Filters", "⑥ Semantic + sort"]
    )

    with tab2:
        st.markdown(
            "**Best match first.** BM25 rewards term frequency but saturates it, and normalizes by "
            "document length, so a short focused listing beats a long keyword-stuffed one."
        )
        with st.form("bm25_f2"):
            q = st.text_input("Query", value="running shoes")
            run = st.form_submit_button("Search")
        if form_submitted("bm25_f2", run):
            show_shop_query(client, q)

    with tab3:
        st.markdown(
            "**Boost a term.** `$weight` multiplies that term's contribution to the score, "
            "lifting waterproof products above the rest."
        )
        with st.form("bm25_f3"):
            c1, c2, c3 = st.columns(3)
            base = c1.text_input("Base term", value="shoes")
            boost = c2.text_input("Boosted term", value="waterproof")
            weight = c3.slider("Weight", 1.0, 5.0, 3.0, 0.5)
            run = st.form_submit_button("Search")
        if form_submitted("bm25_f3", run):
            left, right = st.columns(2)
            with left:
                st.markdown("**Without boost**")
                show_shop_query(client, base)
            with right:
                st.markdown(f"**With `{boost}` × {weight:g}**")
                show_shop_query(client, f"{base} | (({boost}) => {{$weight: {weight:g}}})")

    with tab4:
        st.markdown(
            "**Smart matching.** `jack*` matches by prefix; `%shoos%` tolerates a typo "
            "(edit distance 1). Fuzzy matches score lower than exact ones."
        )
        left, right = st.columns(2)
        with left:
            with st.form("bm25_f4_prefix"):
                q_prefix = st.text_input("Prefix", value="jack*")
                run = st.form_submit_button("Search")
            if form_submitted("bm25_f4_prefix", run):
                show_shop_query(client, q_prefix)
        with right:
            with st.form("bm25_f4_fuzzy"):
                q_fuzzy = st.text_input("Fuzzy", value="%shoos%")
                run = st.form_submit_button("Search")
            if form_submitted("bm25_f4_fuzzy", run):
                show_shop_query(client, q_fuzzy)

    with tab5:
        st.markdown(
            "**Filters vs. score.** A numeric range only removes results; scores stay identical. "
            "A tag match is part of the query, so it adds to the score."
        )
        categories = sorted({c for _, _, c, _ in SHOP_PRODUCTS})
        with st.form("bm25_f5"):
            c1, c2, c3 = st.columns(3)
            term = c1.text_input("Term", value="running")
            max_price = c2.slider("Max price ($)", 10, 200, 50, 5)
            category = c3.selectbox("Category tag", categories, index=categories.index("shoes"))
            run = st.form_submit_button("Search")
        if form_submitted("bm25_f5", run):
            cols = st.columns(3)
            with cols[0]:
                st.markdown("**Text only**")
                show_shop_query(client, term)
            with cols[1]:
                st.markdown("**+ price filter** (same scores)")
                show_shop_query(client, f"{term} @price:[0 {max_price}]")
            with cols[2]:
                st.markdown("**+ category tag** (higher scores)")
                show_shop_query(client, f"{term} @category:{{{category}}}")

    with tab6:
        st.markdown(
            "**Semantic + sort.** Text pre-filters the candidates, then KNN finds the nearest by meaning. "
            "By default results rank by BM25 score; `SORTBY __embedding_score` ranks by vector distance instead."
        )
        st.caption("`$v` is the embedding of the vector query text; products are embedded from title + description.")
        with st.form("bm25_f6"):
            c1, c2, c3 = st.columns([1, 2, 1])
            term = c1.text_input("Text filter", value="running")
            vec_text = c2.text_input("Vector query ($v)", value="something to track my runs")
            k = c3.slider("K", 1, 10, 3)
            run = st.form_submit_button("Search")
        if form_submitted("bm25_f6", run):
            with st.spinner("Embedding query..."):
                v = embed(vec_text)
            knn = f"{term}=>[KNN {k} @embedding $v]"
            params = ("PARAMS", "2", "v", v, "DIALECT", "2")
            left, right = st.columns(2)
            with left:
                st.markdown("**Ranked by BM25 score**")
                show_shop_query(client, knn, *params)
            with right:
                st.markdown("**Ranked by vector distance**")
                show_shop_query(client, knn, "SORTBY", "__embedding_score", *params)

    # Rendered last so it reflects the queries run above.
    with latency_slot:
        render_latency_meter()


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
