"""
Discrepancy Detection Agent for CXR-Grounder.
Compares radiologist reports with AI findings to identify missed or overcalled findings.
Domain: Medical Multimodal AI | Standard: DICOM SR / CheXpert Labeling Standards
"""
import uuid
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from difflib import SequenceMatcher


class DiscrepancyType(str, Enum):
    MISSED_FINDING = "missed_finding"          # AI found, radiologist did not
    OVERCALLED = "overcalled"                   # Radiologist found, AI did not confirm
    SEVERITY_MISMATCH = "severity_mismatch"     # Same finding, different severity
    LOCATION_MISMATCH = "location_mismatch"     # Same finding, different location
    LATERALITY_MISMATCH = "laterality_mismatch" # Same finding, wrong side
    CONCORDANT = "concordant"                   # Agreement between AI and radiologist


class ClinicalSignificance(str, Enum):
    CRITICAL = "critical"       # Potentially life-threatening discrepancy
    SIGNIFICANT = "significant" # Clinically important but not immediately dangerous
    MINOR = "minor"             # Small difference, low clinical impact
    NEGLIGIBLE = "negligible"   # Stylistic or terminological difference


@dataclass
class Discrepancy:
    """A single discrepancy between radiologist and AI findings."""
    discrepancy_id: str
    discrepancy_type: DiscrepancyType
    clinical_significance: ClinicalSignificance
    radiologist_finding: Optional[str]
    ai_finding: Optional[str]
    similarity_score: float
    explanation: str
    recommendation: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discrepancy_id": self.discrepancy_id,
            "discrepancy_type": self.discrepancy_type.value,
            "clinical_significance": self.clinical_significance.value,
            "radiologist_finding": self.radiologist_finding,
            "ai_finding": self.ai_finding,
            "similarity_score": round(self.similarity_score, 4),
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


@dataclass
class DiscrepancyReport:
    """Complete discrepancy analysis report."""
    report_id: str
    study_id: str
    total_radiologist_findings: int
    total_ai_findings: int
    concordant_count: int
    missed_count: int
    overcalled_count: int
    severity_mismatch_count: int
    concordance_rate: float
    discrepancies: List[Discrepancy]
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "study_id": self.study_id,
            "total_radiologist_findings": self.total_radiologist_findings,
            "total_ai_findings": self.total_ai_findings,
            "concordant_count": self.concordant_count,
            "missed_count": self.missed_count,
            "overcalled_count": self.overcalled_count,
            "severity_mismatch_count": self.severity_mismatch_count,
            "concordance_rate": round(self.concordance_rate, 4),
            "discrepancies": [d.to_dict() for d in self.discrepancies],
            "timestamp": self.timestamp,
        }


class DiscrepancyDetector:
    """
    Compares radiologist reports with AI-generated findings to identify
    missed findings, overcalled findings, and severity mismatches.
    """

    # Critical findings that require immediate attention if missed
    CRITICAL_KEYWORDS = {
        "pneumothorax", "tension", "pneumoperitoneum", "free air",
        "aortic dissection", "pulmonary edema", "large effusion",
        "endotracheal tube malposition", "foreign body", "fracture",
    }

    SEVERITY_SCALE = {
        "normal": 0, "no acute": 0, "unremarkable": 0,
        "mild": 1, "small": 1, "minimal": 1,
        "moderate": 2,
        "severe": 3, "large": 3, "extensive": 3, "massive": 3,
    }

    @classmethod
    def _normalize_finding(cls, text: str) -> str:
        """Normalize finding text for comparison."""
        text = text.lower().strip()
        for prefix in ["there is", "there are", "no evidence of", "no significant"]:
            text = text.replace(prefix, "")
        return " ".join(text.split())

    @classmethod
    def _compute_similarity(cls, text_a: str, text_b: str) -> float:
        """Compute text similarity between two findings."""
        norm_a = cls._normalize_finding(text_a)
        norm_b = cls._normalize_finding(text_b)
        return SequenceMatcher(None, norm_a, norm_b).ratio()

    @classmethod
    def _extract_severity(cls, text: str) -> Optional[int]:
        """Extract severity level from finding text."""
        text_lower = text.lower()
        for keyword, level in cls.SEVERITY_SCALE.items():
            if keyword in text_lower:
                return level
        return None

    @classmethod
    def _is_critical_finding(cls, text: str) -> bool:
        """Check if a finding is clinically critical."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in cls.CRITICAL_KEYWORDS)

    @classmethod
    def _determine_significance(cls, finding_text: str, discrepancy_type: DiscrepancyType) -> ClinicalSignificance:
        """Determine clinical significance of a discrepancy."""
        if cls._is_critical_finding(finding_text):
            if discrepancy_type == DiscrepancyType.MISSED_FINDING:
                return ClinicalSignificance.CRITICAL
            return ClinicalSignificance.SIGNIFICANT

        if discrepancy_type == DiscrepancyType.MISSED_FINDING:
            return ClinicalSignificance.SIGNIFICANT
        if discrepancy_type == DiscrepancyType.SEVERITY_MISMATCH:
            return ClinicalSignificance.MINOR
        if discrepancy_type == DiscrepancyType.OVERCALLED:
            return ClinicalSignificance.MINOR
        return ClinicalSignificance.NEGLIGIBLE

    @classmethod
    def compare_findings(
        cls,
        radiologist_findings: List[str],
        ai_findings: List[str],
        similarity_threshold: float = 0.55,
    ) -> DiscrepancyReport:
        """
        Compare radiologist findings with AI findings and generate discrepancy report.
        """
        study_id = str(uuid.uuid4())[:8]
        discrepancies: List[Discrepancy] = []
        matched_rad: Set[int] = set()
        matched_ai: Set[int] = set()
        concordant_count = 0

        # Find matching pairs
        for i, rad_finding in enumerate(radiologist_findings):
            best_score = 0.0
            best_j = -1
            for j, ai_finding in enumerate(ai_findings):
                if j in matched_ai:
                    continue
                score = cls._compute_similarity(rad_finding, ai_finding)
                if score > best_score:
                    best_score = score
                    best_j = j

            if best_score >= similarity_threshold and best_j >= 0:
                matched_rad.add(i)
                matched_ai.add(best_j)

                # Check for severity mismatch
                rad_severity = cls._extract_severity(rad_finding)
                ai_severity = cls._extract_severity(ai_findings[best_j])

                if rad_severity is not None and ai_severity is not None and rad_severity != ai_severity:
                    disc = Discrepancy(
                        discrepancy_id=str(uuid.uuid4())[:8],
                        discrepancy_type=DiscrepancyType.SEVERITY_MISMATCH,
                        clinical_significance=cls._determine_significance(rad_finding, DiscrepancyType.SEVERITY_MISMATCH),
                        radiologist_finding=rad_finding,
                        ai_finding=ai_findings[best_j],
                        similarity_score=best_score,
                        explanation=f"Severity mismatch: radiologist rated {rad_severity}, AI rated {ai_severity}.",
                        recommendation="Review finding with attending radiologist for consensus.",
                    )
                    discrepancies.append(disc)
                else:
                    concordant_count += 1

        # Find missed findings (AI found, radiologist did not)
        for j, ai_finding in enumerate(ai_findings):
            if j not in matched_ai:
                disc = Discrepancy(
                    discrepancy_id=str(uuid.uuid4())[:8],
                    discrepancy_type=DiscrepancyType.MISSED_FINDING,
                    clinical_significance=cls._determine_significance(ai_finding, DiscrepancyType.MISSED_FINDING),
                    radiologist_finding=None,
                    ai_finding=ai_finding,
                    similarity_score=0.0,
                    explanation="AI detected finding not present in radiologist report.",
                    recommendation="Flag for radiologist review - potential missed finding.",
                )
                discrepancies.append(disc)

        # Find overcalled findings (radiologist found, AI did not)
        for i, rad_finding in enumerate(radiologist_findings):
            if i not in matched_rad:
                disc = Discrepancy(
                    discrepancy_id=str(uuid.uuid4())[:8],
                    discrepancy_type=DiscrepancyType.OVERCALLED,
                    clinical_significance=cls._determine_significance(rad_finding, DiscrepancyType.OVERCALLED),
                    radiologist_finding=rad_finding,
                    ai_finding=None,
                    similarity_score=0.0,
                    explanation="Radiologist finding not confirmed by AI analysis.",
                    recommendation="Consider AI model limitations; clinical judgment takes precedence.",
                )
                discrepancies.append(disc)

        missed_count = sum(1 for d in discrepancies if d.discrepancy_type == DiscrepancyType.MISSED_FINDING)
        overcalled_count = sum(1 for d in discrepancies if d.discrepancy_type == DiscrepancyType.OVERCALLED)
        severity_mismatch_count = sum(1 for d in discrepancies if d.discrepancy_type == DiscrepancyType.SEVERITY_MISMATCH)

        total_compared = max(len(radiologist_findings), len(ai_findings))
        concordance_rate = concordant_count / max(total_compared, 1)

        return DiscrepancyReport(
            report_id=str(uuid.uuid4())[:8],
            study_id=study_id,
            total_radiologist_findings=len(radiologist_findings),
            total_ai_findings=len(ai_findings),
            concordant_count=concordant_count,
            missed_count=missed_count,
            overcalled_count=overcalled_count,
            severity_mismatch_count=severity_mismatch_count,
            concordance_rate=concordance_rate,
            discrepancies=discrepancies,
        )
