"""
gad.verify — standalone verification of oracle determinations.

Usage:
    python -m gad.verify https://oracle.parametricdata.io/determination/{uuid}
    python -m gad.verify /path/to/determination.json
"""

from gad.engine.oracle import verify_determination, GENESIS_HASH, verify_chain

__all__ = ["verify_determination", "GENESIS_HASH", "verify_chain"]
