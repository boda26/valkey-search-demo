"""Index management for the Valkey Search demo."""

from typing import Literal
import valkey
from .client import get_client
from .config import config


Language = Literal["english", "german", "french", "spanish", "italian", "portuguese"]


class IndexManager:
    """Manages Valkey Search indexes for the demo."""
    
    def __init__(self, client: valkey.Valkey | None = None):
        self.client = client or get_client()
    
    def create_product_index(
        self,
        index_name: str = config.index_name,
        prefix: str = config.product_prefix,
        language: Language = "english",
        vector_type: Literal["FLOAT32", "FLOAT16", "BFLOAT16"] = "BFLOAT16",
    ) -> None:
        """
        Create a product index with full schema.
        
        Schema:
        - title: TEXT SORTABLE
        - description: TEXT
        - category: TAG (pipe-separated)
        - price: NUMERIC SORTABLE
        - rating: NUMERIC SORTABLE
        - language: TAG
        - embedding: VECTOR HNSW (BFLOAT16 by default for 1.3 demo)
        """
        try:
            self.client.execute_command("FT.DROPINDEX", index_name)
        except valkey.ResponseError:
            pass  # Index doesn't exist
        
        # Build the FT.CREATE command
        # Using BFLOAT16 to demonstrate new 1.3 vector types
        cmd = [
            "FT.CREATE", index_name,
            "ON", "HASH",
            "PREFIX", "1", prefix,
            "LANGUAGE", language,
            "SCHEMA",
            "title", "TEXT", "SORTABLE",
            "description", "TEXT",
            "category", "TAG", "SEPARATOR", "|",
            "price", "NUMERIC", "SORTABLE",
            "rating", "NUMERIC", "SORTABLE",
            "stock", "NUMERIC",
            "language", "TAG",
            "embedding", "VECTOR", "HNSW", "6",
            "TYPE", vector_type,
            "DIM", str(config.embedding_dim),
            "DISTANCE_METRIC", "COSINE",
        ]
        
        self.client.execute_command(*cmd)
        print(f"Created index '{index_name}' with language={language}, vector_type={vector_type}")
    
    def create_multilang_indexes(self) -> None:
        """Create indexes for multiple languages (1.3 multi-language FTS demo)."""
        languages: list[tuple[str, str, Language]] = [
            (config.index_name, config.product_prefix, "english"),
            (config.index_name_de, config.product_prefix_de, "german"),
            (config.index_name_fr, config.product_prefix_fr, "french"),
            (config.index_name_es, config.product_prefix_es, "spanish"),
        ]
        
        for index_name, prefix, language in languages:
            self.create_product_index(index_name, prefix, language)
    
    def drop_index(self, index_name: str) -> None:
        """Drop an index."""
        try:
            self.client.execute_command("FT.DROPINDEX", index_name)
            print(f"Dropped index '{index_name}'")
        except valkey.ResponseError as e:
            print(f"Index '{index_name}' not found: {e}")
    
    def drop_all_indexes(self) -> None:
        """Drop all demo indexes."""
        indexes = [
            config.index_name,
            config.index_name_de,
            config.index_name_fr,
            config.index_name_es,
        ]
        for idx in indexes:
            self.drop_index(idx)
    
    def get_index_info(self, index_name: str = config.index_name) -> dict:
        """Get index information."""
        try:
            info = self.client.execute_command("FT.INFO", index_name)
            # Parse the flat list into a dict
            return dict(zip(info[::2], info[1::2]))
        except valkey.ResponseError as e:
            return {"error": str(e)}
    
    def list_indexes(self) -> list[str]:
        """List all indexes."""
        return self.client.execute_command("FT._LIST")


if __name__ == "__main__":
    # Quick test
    manager = IndexManager()
    manager.create_multilang_indexes()
    print("Indexes:", manager.list_indexes())
