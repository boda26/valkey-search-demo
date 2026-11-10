# Valkey Search 1.3 Demo - Shopping App

A multi-language product search demo showcasing Valkey Search 1.3 features through a realistic e-commerce use case. Includes both a Streamlit web UI and an interactive CLI.

## Features Demonstrated

| Feature | Module | PR |
|---------|--------|-----|
| Multi-language FTS | `features/multilang_fts.py` | [#1263](https://github.com/valkey-io/valkey-search/pull/1263) |
| BM25STD Text Scoring | `features/bm25_scoring.py` | [#1287](https://github.com/valkey-io/valkey-search/pull/1287) |
| Vector Search (FLOAT16/BFLOAT16 + Range) | `features/vector_search.py` | [#1001](https://github.com/valkey-io/valkey-search/pull/1001), [#985](https://github.com/valkey-io/valkey-search/pull/985) |
| FT.HYBRID Search | `features/hybrid_search.py` | [#1083](https://github.com/valkey-io/valkey-search/pull/1083) |
| Paginated Results (Cursors) | `features/cursor_paging.py` | [#1394](https://github.com/valkey-io/valkey-search/pull/1394) |

## Prerequisites

- Docker
- A `libsearch.so` built from the [valkey-search](https://github.com/valkey-io/valkey-search) `1.3` branch (see [Building libsearch.so](#building-libsearchso) below)

## Quick Start (Docker)

### 1. Build `libsearch.so` and place it in this directory

See [Building libsearch.so](#building-libsearchso) for instructions. The file should be at `./libsearch.so`.

### 2. Start everything

```bash
# If you have docker compose (v2 plugin):
docker compose up -d

# If not, start containers manually:
docker network create valkey-demo-net

# Valkey server with search module
docker run -d \
  --name valkey-search-demo \
  --network valkey-demo-net \
  -p 6379:6379 \
  -v ./libsearch.so:/usr/lib/valkey/modules/libsearch.so:ro \
  valkey/valkey:unstable \
  valkey-server \
    --loadmodule /usr/lib/valkey/modules/libsearch.so \
    --save "" --appendonly no

# Streamlit app
docker build -t valkey-search-demo-app .
docker run -d \
  --name valkey-search-demo-app \
  --network valkey-demo-net \
  -p 8501:8501 \
  -e VALKEY_HOST=valkey-search-demo \
  -e VALKEY_PORT=6379 \
  valkey-search-demo-app
```

### 3. Open the app

Open [http://localhost:8501](http://localhost:8501) in your browser.

If you're on a remote dev desktop, forward port 8501 to your local machine:
```bash
# SSH tunnel
ssh -L 8501:localhost:8501 user@your-dev-host
```

### 4. Load sample data

Use the sidebar in the Streamlit UI, or via the CLI:
```bash
docker exec -it valkey-search-demo-app python -m demo.cli
# Then press 's' to set up sample data
```

### 5. Tear down

```bash
docker stop valkey-search-demo valkey-search-demo-app
docker rm valkey-search-demo valkey-search-demo-app
docker network rm valkey-demo-net
```

## Building libsearch.so

The valkey-search 1.3 module requires Valkey >= 9.1.0 (`valkey/valkey:unstable` Docker image) and must be built in a Linux environment compatible with the target container (Debian).

### Option A: Build using the valkey-search dev container (recommended)

If you have [valkey-search](https://github.com/valkey-io/valkey-search) checked out locally with the dev container image built:

```bash
cd /path/to/valkey-search
git checkout upstream/1.3

# Configure and build just the module inside the dev container
docker run --rm -v $(pwd):/workspace -w /workspace valkey-search-dev:latest \
  bash -c "./build.sh --debug --configure --no-build && cd .build-debug && ninja libsearch.so"

# Copy the built module
cp .build-debug/libsearch.so /path/to/valkey-search-demo/
```

### Option B: Build natively on a Debian/Ubuntu host

```bash
cd /path/to/valkey-search
git checkout upstream/1.3

# Install dependencies (see valkey-search README for full list)
sudo apt install -y build-essential g++-12 cmake ninja-build libssl-dev

./build.sh
cp .build-release/libsearch.so /path/to/valkey-search-demo/
```

## Running without Docker

If you prefer to run natively:

```bash
# 1. Start Valkey (>= 9.1.0) with the search module
valkey-server --loadmodule /path/to/libsearch.so --save "" --appendonly no

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run the Streamlit web UI
streamlit run app.py

# 4. Or run the interactive CLI
python -m demo.cli
```

## Project Structure

```
valkey-search-demo/
├── app.py                    # Streamlit web UI
├── docker-compose.yml        # Docker orchestration
├── Dockerfile                # App container image
├── requirements.txt
├── libsearch.so              # valkey-search module (you build this)
├── data/                     # Generated at runtime by data loader
├── core/
│   ├── config.py             # Connection settings, index names
│   ├── client.py             # Valkey client wrapper
│   ├── data_loader.py        # Sample data generation + embedding
│   └── index_manager.py      # FT.CREATE / FT.DROPINDEX
├── features/                 # One module per 1.3 feature
│   ├── base.py               # Abstract base class for demos
│   ├── multilang_fts.py      # Multi-language FTS (Snowball stemmers)
│   ├── bm25_scoring.py       # BM25STD scoring with WITHSCORES
│   ├── vector_search.py      # BFLOAT16 vectors + range queries
│   ├── hybrid_search.py      # FT.HYBRID with RRF/LINEAR fusion
│   └── cursor_paging.py      # WITHCURSOR pagination
├── demo/
│   └── cli.py                # Interactive CLI demo runner
└── tests/
    └── test_features.py
```

## License

Apache 2.0
