"""ClawX evidence-stream research layer."""

from modules.clawx_engine.anomaly_detector import FundingAnomalyDetector
from modules.clawx_engine.clawx_engine import ClawXEngine
from modules.clawx_engine.clawx_logger import log_event
from modules.clawx_engine.clawx_subscriber import ClawXSubscriber
from modules.clawx_engine.hypothesis_builder import HypothesisBuilder
from modules.clawx_engine.scheduler_policy_rules import SchedulerPolicyRules
from modules.clawx_engine.scheduler_policy_writer import SchedulerPolicyWriter
from modules.clawx_engine.signal_adapter import SignalAdapter
from modules.clawx_engine.signal_writer import emit_signal

__all__ = [
    "ClawXEngine",
    "ClawXSubscriber",
    "FundingAnomalyDetector",
    "HypothesisBuilder",
    "SchedulerPolicyRules",
    "SchedulerPolicyWriter",
    "SignalAdapter",
    "emit_signal",
    "log_event",
]
