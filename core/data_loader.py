"""Data loader for the Valkey Search demo."""

import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
import valkey

from .client import get_client, get_binary_client
from .config import config
from .index_manager import IndexManager


class DataLoader:
    """Loads product data into Valkey."""
    
    def __init__(self, client: valkey.Valkey | None = None):
        self.client = client or get_client()
        self.binary_client = get_binary_client()
        self._embedder = None
    
    @property
    def embedder(self):
        """Lazy-load the sentence transformer model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(config.embedding_model)
        return self._embedder
    
    def load_products(
        self,
        data_path: Path | str,
        prefix: str = config.product_prefix,
        generate_embeddings: bool = True,
    ) -> int:
        """
        Load products from a JSON file into Valkey.
        
        Returns the number of products loaded.
        """
        data_path = Path(data_path)
        
        with open(data_path) as f:
            products = json.load(f)
        
        count = 0
        for product in products:
            key = f"{prefix}{product['id']}"
            
            # Generate embedding if needed
            if generate_embeddings and "embedding" not in product:
                text = f"{product['title']} {product.get('description', '')}"
                embedding = self.embedder.encode(text)
                product["embedding"] = self._vector_to_bytes(embedding, dtype="bfloat16")
            elif "embedding" in product and isinstance(product["embedding"], list):
                product["embedding"] = self._vector_to_bytes(
                    np.array(product["embedding"]), dtype="bfloat16"
                )
            
            # Store in Valkey (use binary client for embedding)
            self._hset_with_vector(key, product)
            count += 1
        
        print(f"Loaded {count} products from {data_path}")
        return count
    
    def _hset_with_vector(self, key: str, data: dict[str, Any]) -> None:
        """HSET with proper handling of binary vector data."""
        # Separate vector fields from text fields
        vector_fields = {}
        text_fields = {}
        
        for k, v in data.items():
            if isinstance(v, bytes):
                vector_fields[k] = v
            else:
                text_fields[k] = str(v) if not isinstance(v, str) else v
        
        # Set text fields with string client
        if text_fields:
            self.client.hset(key, mapping=text_fields)
        
        # Set vector fields with binary client
        if vector_fields:
            self.binary_client.hset(key, mapping=vector_fields)
    
    @staticmethod
    def _vector_to_bytes(
        vector: np.ndarray,
        dtype: str = "bfloat16",
    ) -> bytes:
        """
        Convert a numpy vector to bytes for Valkey storage.
        
        Supports: float32, float16, bfloat16 (1.3 feature!)
        """
        if dtype == "float32":
            return vector.astype(np.float32).tobytes()
        elif dtype == "float16":
            return vector.astype(np.float16).tobytes()
        elif dtype == "bfloat16":
            # NumPy doesn't have native bfloat16, so we convert via float32
            # bfloat16 = truncated float32 (keep sign + exponent + 7 mantissa bits)
            f32 = vector.astype(np.float32)
            # View as uint32, shift right 16 bits, cast to uint16
            bf16 = (f32.view(np.uint32) >> 16).astype(np.uint16)
            return bf16.tobytes()
        else:
            raise ValueError(f"Unknown dtype: {dtype}")
    
    @staticmethod
    def _bytes_to_vector(
        data: bytes,
        dtype: str = "bfloat16",
        dim: int = config.embedding_dim,
    ) -> np.ndarray:
        """Convert bytes back to numpy vector."""
        if dtype == "float32":
            return np.frombuffer(data, dtype=np.float32)
        elif dtype == "float16":
            return np.frombuffer(data, dtype=np.float16)
        elif dtype == "bfloat16":
            bf16 = np.frombuffer(data, dtype=np.uint16)
            # Expand back to float32
            f32 = (bf16.astype(np.uint32) << 16).view(np.float32)
            return f32
        else:
            raise ValueError(f"Unknown dtype: {dtype}")
    
    def generate_sample_data(self, output_dir: Path | str = "data") -> None:
        """Generate sample product data for the demo."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # English products
        products_en = [
            {"id": "1001", "title": "Trail Running Shoes - Waterproof", "description": "Lightweight waterproof trail running shoes with excellent grip for mountain terrain", "category": "footwear|running|outdoor", "price": 129.99, "rating": 4.7, "stock": 50, "language": "en"},
            {"id": "1002", "title": "Wireless Noise Cancelling Headphones", "description": "Premium over-ear headphones with active noise cancellation and 30-hour battery life", "category": "electronics|audio", "price": 299.99, "rating": 4.8, "stock": 120, "language": "en"},
            {"id": "1003", "title": "Ergonomic Office Chair", "description": "Adjustable lumbar support mesh office chair for all-day comfort during work", "category": "furniture|office", "price": 449.99, "rating": 4.5, "stock": 35, "language": "en"},
            {"id": "1004", "title": "Stainless Steel Water Bottle", "description": "Double-wall vacuum insulated bottle keeps drinks cold for 24 hours or hot for 12", "category": "kitchen|outdoor", "price": 34.99, "rating": 4.6, "stock": 200, "language": "en"},
            {"id": "1005", "title": "Yoga Mat - Extra Thick", "description": "Non-slip exercise mat with alignment lines, perfect for yoga and pilates", "category": "fitness|yoga", "price": 49.99, "rating": 4.4, "stock": 85, "language": "en"},
            {"id": "1006", "title": "Mechanical Gaming Keyboard", "description": "RGB backlit keyboard with Cherry MX switches for responsive gaming", "category": "electronics|gaming|peripherals", "price": 149.99, "rating": 4.7, "stock": 60, "language": "en"},
            {"id": "1007", "title": "Portable Bluetooth Speaker", "description": "Waterproof speaker with 360-degree sound and 20-hour playtime", "category": "electronics|audio|outdoor", "price": 79.99, "rating": 4.3, "stock": 150, "language": "en"},
            {"id": "1008", "title": "Smart Fitness Watch", "description": "GPS enabled fitness tracker with heart rate monitoring and sleep analysis", "category": "electronics|fitness|wearables", "price": 199.99, "rating": 4.6, "stock": 75, "language": "en"},
            {"id": "1009", "title": "Cotton Blend T-Shirt", "description": "Soft breathable everyday t-shirt available in multiple colors", "category": "clothing|casual", "price": 24.99, "rating": 4.2, "stock": 300, "language": "en"},
            {"id": "1010", "title": "LED Desk Lamp with USB Charging", "description": "Dimmable desk lamp with multiple color temperatures and USB port", "category": "lighting|office|electronics", "price": 45.99, "rating": 4.5, "stock": 90, "language": "en"},
        ]
        
        # German products (translations)
        products_de = [
            {"id": "1001", "title": "Traillaufschuhe - Wasserdicht", "description": "Leichte wasserdichte Traillaufschuhe mit hervorragendem Grip für Berggelände", "category": "schuhe|laufen|outdoor", "price": 129.99, "rating": 4.7, "stock": 50, "language": "de"},
            {"id": "1002", "title": "Kabellose Kopfhörer mit Geräuschunterdrückung", "description": "Premium Over-Ear-Kopfhörer mit aktiver Geräuschunterdrückung und 30 Stunden Akkulaufzeit", "category": "elektronik|audio", "price": 299.99, "rating": 4.8, "stock": 120, "language": "de"},
            {"id": "1003", "title": "Ergonomischer Bürostuhl", "description": "Verstellbarer Mesh-Bürostuhl mit Lordosenstütze für ganztägigen Komfort bei der Arbeit", "category": "möbel|büro", "price": 449.99, "rating": 4.5, "stock": 35, "language": "de"},
            {"id": "1004", "title": "Edelstahl Trinkflasche", "description": "Doppelwandige vakuumisolierte Flasche hält Getränke 24 Stunden kalt oder 12 Stunden heiß", "category": "küche|outdoor", "price": 34.99, "rating": 4.6, "stock": 200, "language": "de"},
            {"id": "1005", "title": "Yogamatte - Extra Dick", "description": "Rutschfeste Trainingsmatte mit Ausrichtungslinien, perfekt für Yoga und Pilates", "category": "fitness|yoga", "price": 49.99, "rating": 4.4, "stock": 85, "language": "de"},
        ]
        
        # French products (translations)
        products_fr = [
            {"id": "1001", "title": "Chaussures de Trail - Imperméables", "description": "Chaussures de trail légères et imperméables avec une excellente adhérence pour les terrains montagneux", "category": "chaussures|course|outdoor", "price": 129.99, "rating": 4.7, "stock": 50, "language": "fr"},
            {"id": "1002", "title": "Casque Sans Fil à Réduction de Bruit", "description": "Casque circum-aural premium avec réduction de bruit active et 30 heures d'autonomie", "category": "électronique|audio", "price": 299.99, "rating": 4.8, "stock": 120, "language": "fr"},
            {"id": "1003", "title": "Chaise de Bureau Ergonomique", "description": "Chaise de bureau en mesh ajustable avec support lombaire pour un confort toute la journée", "category": "mobilier|bureau", "price": 449.99, "rating": 4.5, "stock": 35, "language": "fr"},
            {"id": "1004", "title": "Bouteille d'Eau en Acier Inoxydable", "description": "Bouteille isotherme à double paroi garde les boissons froides 24h ou chaudes 12h", "category": "cuisine|outdoor", "price": 34.99, "rating": 4.6, "stock": 200, "language": "fr"},
            {"id": "1005", "title": "Tapis de Yoga - Extra Épais", "description": "Tapis d'exercice antidérapant avec lignes d'alignement, parfait pour yoga et pilates", "category": "fitness|yoga", "price": 49.99, "rating": 4.4, "stock": 85, "language": "fr"},
        ]
        
        # Write JSON files
        with open(output_dir / "products_en.json", "w") as f:
            json.dump(products_en, f, indent=2)
        
        with open(output_dir / "products_de.json", "w") as f:
            json.dump(products_de, f, indent=2)
        
        with open(output_dir / "products_fr.json", "w") as f:
            json.dump(products_fr, f, indent=2)
        
        print(f"Generated sample data in {output_dir}/")
    
    def load_all_sample_data(self, data_dir: Path | str = "data") -> None:
        """Load all sample data files."""
        data_dir = Path(data_dir)
        
        # Create indexes first
        manager = IndexManager(self.client)
        manager.create_multilang_indexes()
        
        # Load data
        self.load_products(data_dir / "products_en.json", config.product_prefix)
        self.load_products(data_dir / "products_de.json", config.product_prefix_de)
        self.load_products(data_dir / "products_fr.json", config.product_prefix_fr)


if __name__ == "__main__":
    loader = DataLoader()
    
    # Generate sample data if it doesn't exist
    data_dir = Path(__file__).parent.parent / "data"
    if not (data_dir / "products_en.json").exists():
        loader.generate_sample_data(data_dir)
    
    # Load into Valkey
    loader.load_all_sample_data(data_dir)
