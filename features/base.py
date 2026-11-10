"""Base class for feature demos."""

from abc import ABC, abstractmethod
from typing import Any

import valkey

from core.client import get_client
from core.config import config


class FeatureDemo(ABC):
    """
    Base class for all feature demos.
    
    Each feature module should inherit from this and implement:
    - name: Feature name
    - description: Brief description
    - setup(): Any setup needed before running demos
    - run_interactive(): Interactive demo session
    """
    
    name: str = "Base Feature"
    description: str = "Base feature demo"
    
    def __init__(self, client: valkey.Valkey | None = None):
        self.client = client or get_client()
        self.index_name = config.index_name
    
    @abstractmethod
    def setup(self) -> None:
        """Set up any prerequisites for this demo."""
        pass
    
    @abstractmethod
    def run_interactive(self) -> None:
        """Run an interactive demo session."""
        pass
    
    def _execute_search(self, *args) -> list[Any]:
        """Execute an FT.SEARCH command and return results."""
        return self.client.execute_command("FT.SEARCH", *args)
    
    def _execute_aggregate(self, *args) -> list[Any]:
        """Execute an FT.AGGREGATE command and return results."""
        return self.client.execute_command("FT.AGGREGATE", *args)
    
    def _parse_search_results(self, results: list) -> list[dict]:
        """
        Parse FT.SEARCH results into a list of dicts.
        
        Results format: [total_count, key1, [field1, val1, ...], key2, ...]
        """
        if not results or results[0] == 0:
            return []
        
        total = results[0]
        items = []
        
        i = 1
        while i < len(results):
            key = results[i]
            fields = results[i + 1] if i + 1 < len(results) else []
            
            # Convert field list to dict
            item = {"_key": key}
            for j in range(0, len(fields), 2):
                item[fields[j]] = fields[j + 1]
            
            items.append(item)
            i += 2
        
        return items
    
    def _print_results(self, results: list[dict], show_fields: list[str] | None = None) -> None:
        """Pretty print search results."""
        if not results:
            print("No results found.")
            return
        
        print(f"\nFound {len(results)} result(s):\n")
        
        for i, item in enumerate(results, 1):
            print(f"  {i}. {item.get('_key', 'unknown')}")
            
            fields_to_show = show_fields or [k for k in item if not k.startswith("_")]
            for field in fields_to_show:
                if field in item:
                    value = item[field]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 80:
                        value = value[:77] + "..."
                    print(f"     {field}: {value}")
            print()
