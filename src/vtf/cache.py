"""Cache module for storing computed hashes and other metadata."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class HashCache:
    """Cache for storing computed image hashes to avoid recomputation."""
    
    def __init__(self, cache_dir: Path | str = ".cache/vtf"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "hash_cache.json"
        self._cache: dict[str, str] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write cache
    
    def get_hash(self, image_path: Path | str) -> str | None:
        """Get cached hash for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Cached hash string, or None if not found
        """
        key = str(image_path)
        return self._cache.get(key)
    
    def set_hash(self, image_path: Path | str, hash_value: str) -> None:
        """Store hash for an image.
        
        Args:
            image_path: Path to the image file
            hash_value: Hash string to store
        """
        key = str(image_path)
        self._cache[key] = hash_value
        self._save_cache()
    
    def has_hash(self, image_path: Path | str) -> bool:
        """Check if hash exists for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if hash exists in cache
        """
        key = str(image_path)
        return key in self._cache
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def remove(self, image_path: Path | str) -> None:
        """Remove cached hash for an image.
        
        Args:
            image_path: Path to the image file
        """
        key = str(image_path)
        if key in self._cache:
            del self._cache[key]
            self._save_cache()


# Global cache instance
_global_cache: HashCache | None = None


def get_global_cache() -> HashCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = HashCache()
    return _global_cache


def clear_global_cache() -> None:
    """Clear global cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()
        _global_cache = None


__all__ = ["HashCache", "get_global_cache", "clear_global_cache"]
