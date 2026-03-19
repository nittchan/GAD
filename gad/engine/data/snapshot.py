"""SHA-256 of raw input data; pins exact API response for verification."""

from gad.engine.oracle import data_snapshot_hash

__all__ = ["data_snapshot_hash"]
