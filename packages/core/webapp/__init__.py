"""
Webapp package: FastAPI + PWA companion interface.
"""

from packages.core.webapp.app import app, get_state, set_state

__all__ = ["app", "get_state", "set_state"]
