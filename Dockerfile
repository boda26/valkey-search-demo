FROM python:3.12-slim

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary=:all: \
        scipy scikit-learn && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ core/
COPY demo/ demo/
COPY features/ features/
COPY tests/ tests/
COPY app.py .

# Create empty data dir (generated at runtime)
RUN mkdir -p data

ENV VALKEY_HOST=valkey
ENV VALKEY_PORT=6379

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
