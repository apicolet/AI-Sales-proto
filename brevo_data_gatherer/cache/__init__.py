"""
Caching layer with SQLite backend.

This package provides intelligent caching with:
- Source-specific TTLs
- SHA256 hashing for change detection
- Automatic expiration cleanup
- Statistics tracking
"""

from brevo_data_gatherer.cache.manager import CacheManager

__all__ = ["CacheManager"]
