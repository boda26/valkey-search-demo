"""Configuration for the Valkey Search demo."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Demo configuration settings."""
    
    # Valkey connection
    host: str = os.getenv("VALKEY_HOST", "localhost")
    port: int = int(os.getenv("VALKEY_PORT", "6379"))
    password: str | None = os.getenv("VALKEY_PASSWORD")
    
    # Index names
    index_name: str = "products_idx"
    index_name_de: str = "products_de_idx"
    index_name_fr: str = "products_fr_idx"
    index_name_es: str = "products_es_idx"
    
    # Data prefixes
    product_prefix: str = "product:"
    product_prefix_de: str = "product:de:"
    product_prefix_fr: str = "product:fr:"
    product_prefix_es: str = "product:es:"
    
    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    
    # Demo settings
    default_page_size: int = 10
    max_results: int = 100


# Singleton config instance
config = Config()
