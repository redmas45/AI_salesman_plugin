import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import ingestion


def test_sanitize_site_id_normalizes_urlish_input():
    assert ingestion.sanitize_site_id("https_demo_vercel_store") == "https_demo_vercel_store"
    assert ingestion.sanitize_site_id("https://vercelclonedwebsite.vercel.app/") == "https_vercelclonedwebsite_vercel_app"


def test_sync_web_crawl_rejects_missing_host():
    with pytest.raises(ValueError, match="must include a host"):
        ingestion.sync_web_crawl("/relative/path")
