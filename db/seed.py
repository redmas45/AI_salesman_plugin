"""Compatibility facade and CLI wrapper for database seeding."""
from db.bootstrap.seed import *  # noqa: F401,F403
from db.bootstrap.seed import seed

if __name__ == "__main__":
    seed()
