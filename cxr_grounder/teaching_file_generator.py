"""
Teaching File Auto-Generator for CXR-Grounder.
Creates annotated CXR teaching cases by grounding report text to image regions.
Domain: Medical Multimodal AI | Standard: DICOM SR / CheXpert Labeling Standards
"""
import uuid
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

from .visual_grounding_engine import (
    VisualGroundingEngine, GroundedFinding, GroundingResult,
    FindingCategory, GroundingConfidence, BoundingBox,
)


class DifficultyLevel(str, Enum):
    RESIDENT = "resident"          # PGY-1/2 level
    FELLOW = "fellow"              # Subspecialty fellow
    ATTENDING = "attending"        # Advanced case
    MULTIDISCIPLINARY = "multidisciplinary"  # Complex multi-system


class CaseType(str, Enum):
    UNKNOWN = "unknown"            # Present image, ask for diagnosis
    ANNOTATED = "annotated"        # Show findings with annotations
    COMPARISON = "comparison"      # Side-by-side with prior
    QUIZ = "quiz"                  # Multiple choice questions
    DISCUSSION = "discussion"      # Full teaching discussion


@dataclass
class TeachingAnnotation:
    """An annotation overlay for a teaching case."""
    annotation_id: str
    finding: GroundedFinding
    arrow_start: tuple  # (x, y) normalized
    arrow_end: tuple    # (x, y) normalized
    label_text: str
    explanation: str
    teaching_pearl: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "finding": self.finding.to_dict(),
            "arrow_start": {"x": round(self.arrow_start[0], 4), "y": round(self.arrow_start[1], 4)},
            "arrow_end": {"x": round(self.arrow_end[0], 4), "y": round(self.arrow_end[1], 4)},
            "label_text": self.label_text,
            "explanation": self.explanation,
            "teaching_pearl": self.teaching_pearl,
        }


@dataclass
class TeachingQuestion:
    """A quiz question for a teaching case."""
    question_id: str
    question_text: str
    options: List[str]
    correct_index: int
    explanation: str
    difficulty: DifficultyLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "options": self.options,
            "correct_index": self.correct_index,
            "explanation": self.explanation,
            "difficulty": self.difficulty.value,
        }


@dataclass
class TeachingCase:
    """A complete teaching case with annotations and questions."""
    case_id: str
    title: str
    case_type: CaseType
    difficulty: DifficultyLevel
    clinical_history: str
    findings_text: List[str]
    impression: str
    grounding_result: Optional[GroundingResult]
    annotations: List[TeachingAnnotation]
    questions: List[TeachingQuestion]
    differential_diagnosis: List[str]
    teaching_points: List[str]
    references: List[str]
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "case_type": self.case_type.value,
            "difficulty": self.difficulty.value,
            "clinical_history": self.clinical_history,
            "findings_text": self.findings_text,
            "impression": self.impression,
            "grounding_result": self.grounding_result.to_dict() if self.grounding_result else None,
            "annotations": [a.to_dict() for a in self.annotations],
            "questions": [q.to_dict() for q in self.questions],
            "differential_diagnosis": self.differential_diagnosis,
            "teaching_points": self.teaching_points,
            "references": self.references,
            "created_at": self.created_at,
        }


class TeachingFileGenerator:
    """
    Auto-generates annotated CXR teaching cases by grounding
    report text to image regions with educational annotations.
    """

    # Teaching pearls by finding category
    TEACHING_PEARLS: Dict[str, List[str]] = {
        "pneumothorax": [
            "Look for the visceral pleural line separated from the chest wall.",
            "Expiratory films increase sensitivity for small pneumothoraces.",
            "Tension pneumothorax shows mediastinal shift away from the affected side.",
        ],
        "pleural_effusion": [
            "Meniscus sign is characteristic of free-flowing pleural effusion.",
            "Blunting of the costophrenic angle requires ~200-300 mL of fluid.",
            "Layering effusion on lateral decubitus confirms free-flowing nature.",
        ],
        "cardiomegaly": [
            "Cardiothoracic ratio > 0.5 on PA film suggests cardiomegaly.",
            "Portable AP films magnify the cardiac silhouette - account for projection.",
            "Consider pericardial effusion vs. true chamber dilation.",
        ],
        "consolidation": [
            "Air bronchograms help distinguish consolidation from pleural effusion.",
            "Silhouette sign helps localize the lobe involved.",
            "Consider pneumonia, pulmonary edema, or hemorrhage in the differential.",
        ],
        "pneumonia": [
            "Lobar consolidation with air bronchograms is classic for bacterial pneumonia.",
            "Round pneumonia is more common in children than adults.",
            "Consider TB if upper lobe involvement with cavitation.",
        ],
        "nodule": [
            "Multiple nodules suggest metastases, granulomas, or vasculitis.",
            "Calcification patterns help distinguish benign from suspicious nodules.",
            "Compare with prior studies to assess stability over 2 years.",
        ],
        "fracture": [
            "Rib fractures may not be visible on initial radiographs.",
            "Check for associated pneumothorax or hemothorax.",
            "Stress fractures show periosteal reaction without a clear fracture line.",
        ],
    }

    # Differential diagnosis mapping
    DIFFERENTIAL_DIAGNOSES: Dict[str, List[str]] = {
        "pneumothorax": ["Bullous disease", "Skin fold artifact", "Pneumomediastinum"],
        "pleural_effusion": ["Ascites with elevated hemidiaphragm", "Lung mass", "Pleural thickening"],
        "cardiomegaly": ["Pericardial effusion", "AP projection magnification", "Normal variant"],
        "consolidation": ["Atelectasis", "Pulmonary edema", "Lung mass", "Pneumonia"],
        "nodule": ["Granuloma", "Primary lung cancer", "Metastasis", "AV malformation"],
        "fracture": ["Normal variant", "Old healed fracture", "Bone island"],
    }

    @classmethod
    def _generate_teaching_pearl(cls, finding_text: str) -> str:
        """Generate a teaching pearl for a finding."""
        text_lower = finding_text.lower()
        for keyword, pearls in cls.TEACHING_PEARLS.items():
            if keyword in text_lower:
                return pearls[0]  # Return the first pearl
        return "Systematic review of all lung zones is essential for comprehensive CXR interpretation."

    @classmethod
    def _generate_arrow_position(cls, bbox: BoundingBox) -> tuple:
        """Generate arrow position pointing to the finding center."""
        center = bbox.center
        # Arrow starts from outside the bbox and points to center
        offset = 0.08
        start = (center[0] + offset, center[1] - offset)
        return (start, center)

    @classmethod
    def _generate_quiz_question(cls, finding: GroundedFinding) -> TeachingQuestion:
        """Generate a quiz question for a finding."""
        category = finding.category.value
        text = finding.finding_text

        question_text = f"What is the most likely finding described: '{text}'?"
        options = [text, "Normal variant", "Artifact", "No significant finding"]
        correct_index = 0

        return TeachingQuestion(
            question_id=str(uuid.uuid4())[:8],
            question_text=question_text,
            options=options,
            correct_index=correct_index,
            explanation=f"The correct answer is based on the characteristic appearance of {category} findings.",
            difficulty=DifficultyLevel.RESIDENT,
        )

    @classmethod
    def generate_case(
        cls,
        study_id: str,
        clinical_history: str,
        findings_text: List[str],
        impression: str,
        case_type: CaseType = CaseType.ANNOTATED,
        difficulty: DifficultyLevel = DifficultyLevel.RESIDENT,
    ) -> TeachingCase:
        """Generate a complete teaching case from a CXR report."""
        # Ground findings to image regions
        grounding_result = VisualGroundingEngine.ground_report(study_id, findings_text)

        # Generate annotations
        annotations = []
        for finding in grounding_result.findings:
            arrow_start, arrow_end = cls._generate_arrow_position(finding.bounding_box)
            pearl = cls._generate_teaching_pearl(finding.finding_text)

            annotation = TeachingAnnotation(
                annotation_id=str(uuid.uuid4())[:8],
                finding=finding,
                arrow_start=arrow_start,
                arrow_end=arrow_end,
                label_text=finding.finding_text[:60],
                explanation=f"This {finding.category.value} finding is located in the {finding.location_anatomy or 'chest'} region.",
                teaching_pearl=pearl,
            )
            annotations.append(annotation)

        # Generate quiz questions
        questions = []
        if case_type in (CaseType.QUIZ, CaseType.DISCUSSION):
            for finding in grounding_result.findings[:3]:  # Max 3 questions
                questions.append(cls._generate_quiz_question(finding))

        # Generate differential diagnoses
        differentials = []
        for finding in grounding_result.findings:
            text_lower = finding.finding_text.lower()
            for keyword, diffs in cls.DIFFERENTIAL_DIAGNOSES.items():
                if keyword in text_lower:
                    differentials.extend(diffs)
                    break
        differentials = list(set(differentials))[:5]

        # Generate teaching points
        teaching_points = [
            "Always correlate imaging findings with clinical history.",
            "Systematic approach prevents missed findings.",
            "Comparison with prior studies is invaluable for change detection.",
        ]
        for finding in grounding_result.findings[:2]:
            teaching_points.append(cls._generate_teaching_pearl(finding.finding_text))

        return TeachingCase(
            case_id=str(uuid.uuid4())[:8],
            title=f"Teaching Case: {impression[:80]}",
            case_type=case_type,
            difficulty=difficulty,
            clinical_history=clinical_history,
            findings_text=findings_text,
            impression=impression,
            grounding_result=grounding_result,
            annotations=annotations,
            questions=questions,
            differential_diagnosis=differentials,
            teaching_points=teaching_points,
            references=[
                "Felson's Principles of Chest Roentgenology",
                "ACR Appropriateness Criteria",
                "Radiopaedia.org Chest X-ray Atlas",
            ],
        )
