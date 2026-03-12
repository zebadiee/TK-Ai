"""Gateway services for remote read-only cluster access."""

from .evidence_reader import derive_follow_up_signals, read_recent_evidence

__all__ = ["derive_follow_up_signals", "read_recent_evidence"]
