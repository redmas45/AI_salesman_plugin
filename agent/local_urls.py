"""URL helpers for local development hosts used from Docker and host runtimes."""

from __future__ import annotations

from urllib.parse import urlparse


LOCALHOST_NAMES = {"127.0.0.1", "localhost"}
DOCKER_HOST_NAME = "host.docker.internal"


def local_runtime_url_candidates(url: str) -> list[str]:
    """Return URL candidates that let Docker reach host-local dev servers.

    The original URL is always first. For normal production domains this returns
    one item. For localhost URLs it also adds the Docker Desktop host alias.
    """
    clean_url = str(url or "").strip()
    if not clean_url:
        return []

    candidates = [clean_url]
    try:
        parsed = urlparse(clean_url)
    except ValueError:
        return candidates

    if parsed.hostname in LOCALHOST_NAMES:
        port = f":{parsed.port}" if parsed.port else ""
        candidates.append(parsed._replace(netloc=f"{DOCKER_HOST_NAME}{port}").geturl())

    return list(dict.fromkeys(candidates))
