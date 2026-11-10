"""
Tests for Valkey Search 1.3 feature demos.

These tests verify the demo code works correctly against a running Valkey instance.
Skip these tests if Valkey is not available.
"""

import pytest

# Try to import valkey and check connection
try:
    import valkey
    from core.client import get_client
    
    client = get_client()
    client.ping()
    VALKEY_AVAILABLE = True
except Exception:
    VALKEY_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not VALKEY_AVAILABLE,
    reason="Valkey server not available"
)


class TestIndexManager:
    """Test index management functionality."""
    
    def test_create_index(self):
        """Test index creation."""
        from core.index_manager import IndexManager
        
        manager = IndexManager()
        manager.create_product_index("test_idx", "test:", "english")
        
        # Verify index exists
        indexes = manager.list_indexes()
        assert "test_idx" in indexes
        
        # Cleanup
        manager.drop_index("test_idx")
    
    def test_multilang_indexes(self):
        """Test multi-language index creation."""
        from core.index_manager import IndexManager
        from core.config import config
        
        manager = IndexManager()
        manager.create_multilang_indexes()
        
        indexes = manager.list_indexes()
        assert config.index_name in indexes
        assert config.index_name_de in indexes
        assert config.index_name_fr in indexes
        
        # Cleanup
        manager.drop_all_indexes()


class TestDataLoader:
    """Test data loading functionality."""
    
    def test_generate_sample_data(self, tmp_path):
        """Test sample data generation."""
        from core.data_loader import DataLoader
        
        loader = DataLoader()
        loader.generate_sample_data(tmp_path)
        
        assert (tmp_path / "products_en.json").exists()
        assert (tmp_path / "products_de.json").exists()
        assert (tmp_path / "products_fr.json").exists()
    
    def test_vector_conversion(self):
        """Test vector to bytes conversion for different types."""
        import numpy as np
        from core.data_loader import DataLoader
        
        vec = np.random.randn(384).astype(np.float32)
        
        # Test FLOAT32
        f32_bytes = DataLoader._vector_to_bytes(vec, "float32")
        assert len(f32_bytes) == 384 * 4
        
        # Test FLOAT16
        f16_bytes = DataLoader._vector_to_bytes(vec, "float16")
        assert len(f16_bytes) == 384 * 2
        
        # Test BFLOAT16
        bf16_bytes = DataLoader._vector_to_bytes(vec, "bfloat16")
        assert len(bf16_bytes) == 384 * 2


class TestMultiLangFTS:
    """Test multi-language full-text search."""
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Set up test data."""
        from core.data_loader import DataLoader
        from core.index_manager import IndexManager
        from pathlib import Path
        
        manager = IndexManager()
        loader = DataLoader()
        
        # Create indexes
        manager.create_multilang_indexes()
        
        # Load sample data
        data_dir = Path(__file__).parent.parent / "data"
        if (data_dir / "products_en.json").exists():
            loader.load_all_sample_data(data_dir)
        
        yield
        
        # Cleanup is optional for demo purposes
    
    def test_english_search(self):
        """Test English full-text search."""
        from features.multilang_fts import MultiLangFTSDemo
        
        demo = MultiLangFTSDemo()
        results = demo.demo_english_search("running shoes")
        
        # Should find at least one result
        assert len(results) > 0


class TestBM25Scoring:
    """Test BM25 scoring functionality."""
    
    def test_search_with_scores(self):
        """Test that scores are returned with WITHSCORES."""
        from features.bm25_scoring import BM25ScoringDemo
        
        demo = BM25ScoringDemo()
        results = demo.demo_search_with_scores("waterproof")
        
        # Results should have scores
        for result in results:
            assert "_score" in result


class TestCursorPaging:
    """Test cursor-based pagination."""
    
    def test_cursor_results_parsing(self):
        """Test cursor result parsing."""
        from features.cursor_paging import CursorPagingDemo
        
        demo = CursorPagingDemo()
        
        # Mock cursor results format
        mock_results = [
            [10, "key1", ["title", "Test Product"], "key2", ["title", "Another Product"]],
            12345  # cursor_id
        ]
        
        cursor_id, items = demo._parse_cursor_results(mock_results)
        
        assert cursor_id == 12345
        assert len(items) == 2
        assert items[0]["title"] == "Test Product"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
