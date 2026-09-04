"""
Pydantic v2 schemas and data definitions for Cxr Multimodal Report Grounder.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import datetime
import re
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

# Allowed pattern for task_id and target_identifier: alphanumeric, hyphens, underscores
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$")
# Metric bounds for validation
_METRIC_MIN = -1e6
_METRIC_MAX = 1e6


class UrgencyLevel(str, Enum):
    ROUTINE = "ROUTINE"
    ELEVATED = "ELEVATED_RISK"
    CRITICAL_STAT = "CRITICAL_STAT_PANIC"


class SystemIntegrityStatus(str, Enum):
    VALIDATED = "VALIDATED_OPTIMAL"
    DISCORDANT = "DISCORDANT_ANOMALY"
    RECALIBRATION_REQUIRED = "RECALIBRATION_REQUIRED"


class SystemTaskPayload(BaseModel):
    task_id: str = Field(..., description="Unique task / case identifier")
    target_identifier: str = Field(..., description="Entity, patient key, or genomic/cryptographic target")
    primary_metric: float = Field(..., description="Primary domain measurement or score")
    secondary_metric: float = Field(default=0.0, description="Secondary kinetic or confidence score")
    status_descriptor: str = Field(default="NOMINAL", description="Status code or phenotype descriptor")
    is_critical_flag: bool = Field(default=False, description="Emergency escalation or high priority trigger")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Metadata key-value pairs")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    @field_validator("task_id", "target_identifier")
    @classmethod
    def validate_safe_identifier(cls, v: str) -> str:
        if not _SAFE_ID_PATTERN.match(v):
            raise ValueError(
                f"Identifier must be 1-64 chars, alphanumeric/hyphen/underscore, "
                f"starting with alphanumeric. Got: {v!r}"
            )
        return v

    @field_validator("primary_metric", "secondary_metric")
    @classmethod
    def validate_metric_bounds(cls, v: float) -> float:
        if not isinstance(v, (int, float)):
            raise ValueError(f"Metric must be numeric, got {type(v).__name__}")
        if v != v:  # NaN check
            raise ValueError("Metric must not be NaN")
        if v == float("inf") or v == float("-inf"):
            raise ValueError("Metric must be finite")
        if v < _METRIC_MIN or v > _METRIC_MAX:
            raise ValueError(f"Metric must be between {_METRIC_MIN} and {_METRIC_MAX}")
        return float(v)


class AgentAlert(BaseModel):
    alert_id: str
    origin_worker: str
    urgency: UrgencyLevel
    summary: str
    technical_details: str
    actionable_remediation: str
    standard_reference: str = "CAP / CLSI / ISO Standards"
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ConsensusDossier(BaseModel):
    dossier_id: str
    system_slug: str = "cxr-multimodal-report-grounder"
    domain: str = "Clinical & Biomedical AI"
    task_id: str
    target_identifier: str
    overall_urgency: UrgencyLevel
    integrity_status: SystemIntegrityStatus
    total_alerts: int
    critical_alerts_count: int
    alerts: List[AgentAlert]
    standard_reference: str = "CAP / CLSI / ISO Standards"
    consensus_summary: str
    audit_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
