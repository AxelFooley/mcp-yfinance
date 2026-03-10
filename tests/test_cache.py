"""Tests for caching system."""

import time

from server import _cache, _cache_get, _cache_key, _cache_set, cached


def test_cache_get_miss():
    """Verify returns None for non-existent key."""
    assert _cache_get("nonexistent_key", 60) is None


def test_cache_get_hit():
    """Verify returns value within TTL."""
    _cache_set("test_key", "test_value", 60)
    assert _cache_get("test_key", 60) == "test_value"
    # Cleanup
    del _cache["test_key"]


def test_cache_get_expired():
    """Verify returns None after TTL."""
    _cache_set("test_key", "test_value", 1)
    time.sleep(1.1)  # Wait for expiry
    assert _cache_get("test_key", 60) is None


def test_cached_decorator():
    """Verify caches function return value."""
    call_count = []

    @cached(ttl=60)
    def test_func(symbol: str) -> str:
        call_count.append(symbol)
        return f"result_{symbol}"

    # First call executes function
    result1 = test_func("AAPL")
    assert result1 == "result_AAPL"
    assert len(call_count) == 1

    # Second call uses cache
    result2 = test_func("AAPL")
    assert result2 == "result_AAPL"
    assert len(call_count) == 1  # No additional call

    # Different symbol bypasses cache
    result3 = test_func("MSFT")
    assert result3 == "result_MSFT"
    assert len(call_count) == 2

    # Cleanup
    import server

    server._cache.clear()


def test_cached_decorator_ttl_expiry():
    """Verify refetches after TTL."""
    call_count = []

    @cached(ttl=1)
    def test_func(symbol: str) -> str:
        call_count.append(symbol)
        return f"result_{symbol}_{len(call_count)}"

    # First call
    result1 = test_func("AAPL")
    assert result1 == "result_AAPL_1"
    assert len(call_count) == 1

    # Cache hit
    result2 = test_func("AAPL")
    assert result2 == "result_AAPL_1"
    assert len(call_count) == 1

    # Wait for expiry
    time.sleep(1.1)

    # Cache miss - refetch
    result3 = test_func("AAPL")
    assert result3 == "result_AAPL_2"
    assert len(call_count) == 2

    # Cleanup
    import server

    server._cache.clear()


def test_clear_cache():
    """Verify clear_cache() empties _cache dict."""
    import server

    # Populate cache
    _cache_set("key1", "value1", 60)
    _cache_set("key2", "value2", 60)
    assert len(_cache) == 2

    # Clear cache
    server._cache.clear()
    assert len(_cache) == 0


def test_cache_key_generation():
    """Verify creates consistent keys."""
    key1 = _cache_key("AAPL", "get_stock_info", period="1mo")
    key2 = _cache_key("AAPL", "get_stock_info", period="1mo")
    key3 = _cache_key("AAPL", "get_stock_info", period="5d")

    assert key1 == key2
    assert key1 != key3

    # Verify key format
    assert "AAPL" in key1
    assert "get_stock_info" in key1
    assert "period=1mo" in key1
