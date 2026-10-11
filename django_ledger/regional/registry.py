"""
Resolve the active regional plugin for the running process.

``django_ledger_countries`` is optional at install time; imports are declared here
(not inside function bodies) so missing packages fail predictably at first plugin use.
"""
from __future__ import annotations

from functools import lru_cache

from django_ledger.regional.base import RegionalPlugin
from django_ledger.regional.us_fallback import USRegionalPlugin

try:
    from django_ledger_countries.registry import (
        clear_active_plugin_cache as _clear_countries_plugin_cache,
        get_active_plugin as _get_countries_plugin,
    )
except ImportError:
    _get_countries_plugin = None
    _clear_countries_plugin_cache = None


@lru_cache(maxsize=1)
def get_country_plugin() -> RegionalPlugin:
    """
    Return the active :class:`RegionalPlugin`.

    Delegates to ``django_ledger_countries`` when installed; otherwise returns
    the built-in US passthrough plugin.
    """
    if _get_countries_plugin is not None:
        return _get_countries_plugin()
    return USRegionalPlugin()


def clear_country_plugin_cache() -> None:
    """Clear the plugin cache (useful in tests)."""
    get_country_plugin.cache_clear()
    if _clear_countries_plugin_cache is not None:
        _clear_countries_plugin_cache()
