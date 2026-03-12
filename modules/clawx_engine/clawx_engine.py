"""ClawX evidence analysis engine."""

from __future__ import annotations

from typing import Any

from modules.clawx_engine.anomaly_detector import FundingAnomalyDetector
from modules.clawx_engine.hypothesis_builder import HypothesisBuilder
from modules.clawx_engine.clawx_logger import log_event
from modules.clawx_engine.scheduler_policy_rules import SchedulerPolicyRules
from modules.clawx_engine.scheduler_policy_writer import SchedulerPolicyWriter
from modules.clawx_engine.signal_writer import emit_signal as write_signal


class ClawXEngine:
    """Processes evidence-stream events and emits follow-up signals."""

    def __init__(
        self,
        signal_adapter: Any,
        anomaly_detector: FundingAnomalyDetector | None = None,
        hypothesis_builder: HypothesisBuilder | None = None,
        scheduler_policy_rules: SchedulerPolicyRules | None = None,
        scheduler_policy_writer: SchedulerPolicyWriter | None = None,
    ) -> None:
        self.signal_adapter = signal_adapter
        self.anomaly_detector = anomaly_detector or FundingAnomalyDetector()
        self.hypothesis_builder = hypothesis_builder or HypothesisBuilder()
        self._recent_observations: list[Any] = []
        self._signal_history: list[dict[str, Any]] = []
        self._evidence_history: list[dict[str, Any]] = []
        self.scheduler_policy_writer = scheduler_policy_writer
        if scheduler_policy_rules is not None:
            self.scheduler_policy_rules = scheduler_policy_rules
        elif scheduler_policy_writer is not None:
            self.scheduler_policy_rules = SchedulerPolicyRules(
                self._signal_history,
                self._evidence_history,
                scheduler_policy_writer,
            )
        else:
            self.scheduler_policy_rules = None

    def process_event(self, event: Any) -> None:
        event_type = getattr(event, "type", "")
        log_event(
            "analysis_start",
            entity=self._entity_for_event(event),
            trace_id=getattr(event, "trace_id", None),
            event_type=event_type,
        )
        if event_type == "observation":
            self._process_observation(event)
        elif event_type == "claim":
            self._process_claim(event)
        self._evaluate_policy()

    def _process_observation(self, evidence: Any) -> None:
        self._recent_observations.append(evidence)
        self._record_evidence_event(evidence, "observation")

        if self.anomaly_detector.detect(evidence):
            log_event(
                "pattern_detected",
                pattern="funding_rate_spike",
                exchange=getattr(evidence, "content", {}).get("exchange"),
                trace_id=getattr(evidence, "trace_id", None),
            )
            self._emit_signal(
                signal_type="funding_rate_anomaly",
                payload=getattr(evidence, "content", {}),
                severity="high",
                trace_id=getattr(evidence, "trace_id", None),
            )

        hypothesis = self.hypothesis_builder.build(self._recent_observations)
        if hypothesis is not None:
            log_event(
                "hypothesis_generated",
                hypothesis=str(hypothesis.get("type", "")),
                trace_id=getattr(evidence, "trace_id", None),
            )
            self._emit_signal(
                signal_type=str(hypothesis["type"]),
                payload=hypothesis,
                severity="medium",
                trace_id=getattr(evidence, "trace_id", None),
            )
            self._recent_observations.clear()

    def _process_claim(self, claim: Any) -> None:
        self._record_evidence_event(claim, "claim")
        confidence = getattr(claim, "confidence", 1.0)
        if isinstance(confidence, (int, float)) and float(confidence) < 0.4:
            self._emit_signal(
                signal_type="low_confidence_claim",
                payload={"claim_id": getattr(claim, "claim_id", None)},
                severity="medium",
                trace_id=getattr(claim, "trace_id", None),
            )

    def _emit_signal(
        self,
        *,
        signal_type: str,
        payload: dict[str, Any],
        severity: str,
        trace_id: str | None,
    ) -> None:
        signal = self.signal_adapter.emit(
            signal_type=signal_type,
            payload=payload,
            severity=severity,
            trace_id=trace_id,
        )
        if isinstance(signal, dict):
            self._signal_history.append(signal)
            signal_payload = signal.get("payload", {})
            if not isinstance(signal_payload, dict):
                signal_payload = {}
            write_signal(
                signal_type=signal_type,
                payload=signal_payload,
                source=signal.get("source"),
                severity=severity,
                trace_id=trace_id,
                signal_id=signal.get("signal_id"),
            )
        log_event(
            "signal_emitted",
            signal=signal_type,
            severity=severity,
            trace_id=trace_id,
        )

    def _record_evidence_event(self, event: Any, event_type: str) -> None:
        content = getattr(event, "content", {})
        if not isinstance(content, dict):
            content = {}
        self._evidence_history.append(
            {
                "type": event_type,
                "timestamp": getattr(event, "timestamp", 0),
                "trace_id": getattr(event, "trace_id", None),
                "content": content,
            }
        )

    def _evaluate_policy(self) -> None:
        if self.scheduler_policy_rules is None:
            return
        self.scheduler_policy_rules.evaluate()

    def _entity_for_event(self, event: Any) -> str | None:
        content = getattr(event, "content", {})
        if isinstance(content, dict):
            for key in ("asset", "symbol", "exchange"):
                value = content.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return None
