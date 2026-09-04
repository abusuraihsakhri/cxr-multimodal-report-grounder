"""
Automated Pytest for CXR-Grounder Visual Grounding & Discrepancy Detection.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cxr_grounder.discrepancy_detector import (
    DiscrepancyDetector, DiscrepancyType, ClinicalSignificance
)
from cxr_grounder.visual_grounding_engine import (
    VisualGroundingEngine, FindingCategory, GroundingConfidence, BoundingBox
)
from cxr_grounder.teaching_file_generator import (
    TeachingFileGenerator, CaseType, DifficultyLevel
)


class TestDiscrepancyDetector:
    def test_concordant_findings(self):
        rad = ["Normal heart size", "No pneumothorax"]
        ai = ["Normal heart size", "No pneumothorax"]
        report = DiscrepancyDetector.compare_findings(rad, ai, similarity_threshold=0.55)
        assert report.concordant_count == 2
        assert report.missed_count == 0
        assert report.overcalled_count == 0

    def test_missed_finding(self):
        rad = ["Normal heart size"]
        ai = ["Normal heart size", "Right lower lobe consolidation"]
        report = DiscrepancyDetector.compare_findings(rad, ai, similarity_threshold=0.55)
        assert report.missed_count == 1
        assert report.concordant_count == 1

    def test_overcalled_finding(self):
        rad = ["Normal heart size", "Left upper lobe nodule"]
        ai = ["Normal heart size"]
        report = DiscrepancyDetector.compare_findings(rad, ai, similarity_threshold=0.55)
        assert report.overcalled_count == 1

    def test_severity_mismatch(self):
        rad = ["Mild pleural effusion"]
        ai = ["Severe pleural effusion"]
        report = DiscrepancyDetector.compare_findings(rad, ai, similarity_threshold=0.55)
        assert report.severity_mismatch_count >= 1

    def test_critical_finding_significance(self):
        rad = []
        ai = ["Tension pneumothorax detected"]
        report = DiscrepancyDetector.compare_findings(rad, ai, similarity_threshold=0.55)
        assert report.missed_count == 1
        assert report.discrepancies[0].clinical_significance == ClinicalSignificance.CRITICAL

    def test_empty_findings(self):
        report = DiscrepancyDetector.compare_findings([], [], similarity_threshold=0.55)
        assert report.concordant_count == 0
        assert report.concordance_rate == 0.0

    def test_report_serialization(self):
        rad = ["Normal heart size"]
        ai = ["Normal heart size"]
        report = DiscrepancyDetector.compare_findings(rad, ai, similarity_threshold=0.55)
        d = report.to_dict()
        assert "report_id" in d
        assert "concordance_rate" in d


class TestVisualGroundingEngine:
    def test_classify_finding_cardiac(self):
        assert VisualGroundingEngine.classify_finding("Cardiomegaly noted") == FindingCategory.CARDIAC

    def test_classify_finding_pulmonary(self):
        assert VisualGroundingEngine.classify_finding("Right lower lobe pneumonia") == FindingCategory.PULMONARY

    def test_classify_finding_pleural(self):
        assert VisualGroundingEngine.classify_finding("Pleural effusion") == FindingCategory.PLEURAL

    def test_classify_finding_other(self):
        assert VisualGroundingEngine.classify_finding("Something unusual") == FindingCategory.OTHER

    def test_determine_laterality_right(self):
        assert VisualGroundingEngine.determine_laterality("Right upper lobe opacity") == "right"

    def test_determine_laterality_left(self):
        assert VisualGroundingEngine.determine_laterality("Left lower lobe collapse") == "left"

    def test_determine_laterality_bilateral(self):
        assert VisualGroundingEngine.determine_laterality("Bilateral infiltrates") == "bilateral"

    def test_determine_laterality_none(self):
        assert VisualGroundingEngine.determine_laterality("Cardiomegaly") is None

    def test_ground_finding_cardiac(self):
        finding = VisualGroundingEngine.ground_finding("Cardiomegaly", confidence=0.9)
        assert finding.category == FindingCategory.CARDIAC
        assert finding.grounding_confidence == GroundingConfidence.HIGH
        assert finding.bounding_box.area > 0

    def test_ground_finding_pleural(self):
        finding = VisualGroundingEngine.ground_finding("Right pleural effusion", confidence=0.7)
        assert finding.category == FindingCategory.PLEURAL
        assert finding.laterality == "right"

    def test_ground_finding_low_confidence(self):
        finding = VisualGroundingEngine.ground_finding("Possible nodule", confidence=0.2)
        assert finding.grounding_confidence == GroundingConfidence.UNCERTAIN

    def test_ground_report(self):
        findings = ["Cardiomegaly", "Right pleural effusion", "Normal lungs"]
        result = VisualGroundingEngine.ground_report("STUDY-001", findings)
        assert result.total_findings == 3
        assert result.study_id == "STUDY-001"
        assert result.grounding_rate > 0

    def test_ground_report_empty(self):
        result = VisualGroundingEngine.ground_report("STUDY-002", [])
        assert result.total_findings == 0

    def test_ground_report_whitespace_filtered(self):
        result = VisualGroundingEngine.ground_report("STUDY-003", ["  ", "Cardiomegaly", ""])
        assert result.total_findings == 1

    def test_iou_overlapping(self):
        box_a = BoundingBox(0.0, 0.0, 0.5, 0.5)
        box_b = BoundingBox(0.25, 0.25, 0.75, 0.75)
        iou = VisualGroundingEngine.compute_iou(box_a, box_b)
        assert 0 < iou < 1

    def test_iou_no_overlap(self):
        box_a = BoundingBox(0.0, 0.0, 0.1, 0.1)
        box_b = BoundingBox(0.9, 0.9, 1.0, 1.0)
        iou = VisualGroundingEngine.compute_iou(box_a, box_b)
        assert iou == 0.0

    def test_iou_identical(self):
        box_a = BoundingBox(0.0, 0.0, 0.5, 0.5)
        box_b = BoundingBox(0.0, 0.0, 0.5, 0.5)
        iou = VisualGroundingEngine.compute_iou(box_a, box_b)
        assert iou == 1.0

    def test_bounding_box_properties(self):
        bbox = BoundingBox(0.1, 0.2, 0.6, 0.8)
        assert bbox.width == pytest.approx(0.5)
        assert bbox.height == pytest.approx(0.6)
        assert bbox.center == (pytest.approx(0.35), pytest.approx(0.5))
        assert bbox.area == pytest.approx(0.3)


class TestTeachingFileGenerator:
    def test_generate_basic_case(self):
        case = TeachingFileGenerator.generate_case(
            study_id="STUDY-TEACH-001",
            clinical_history="Chest pain",
            findings_text=["Cardiomegaly", "Clear lungs"],
            impression="Cardiomegaly"
        )
        assert case.case_id is not None
        assert len(case.findings_text) == 2
        assert case.grounding_result is not None

    def test_generate_quiz_case(self):
        case = TeachingFileGenerator.generate_case(
            study_id="STUDY-TEACH-002",
            clinical_history="Dyspnea",
            findings_text=["Right pleural effusion"],
            impression="Right pleural effusion",
            case_type=CaseType.QUIZ
        )
        assert len(case.questions) > 0

    def test_generate_annotated_case(self):
        case = TeachingFileGenerator.generate_case(
            study_id="STUDY-TEACH-003",
            clinical_history="Cough",
            findings_text=["Left lower lobe consolidation"],
            impression="Left lower lobe pneumonia",
            case_type=CaseType.ANNOTATED
        )
        assert len(case.annotations) > 0

    def test_case_serialization(self):
        case = TeachingFileGenerator.generate_case(
            study_id="STUDY-TEACH-004",
            clinical_history="Follow-up",
            findings_text=["Stable nodule"],
            impression="Stable nodule"
        )
        d = case.to_dict()
        assert "case_id" in d
        assert "grounding_result" in d
        assert "annotations" in d

    def test_differential_diagnosis_generated(self):
        case = TeachingFileGenerator.generate_case(
            study_id="STUDY-TEACH-005",
            clinical_history="Acute dyspnea",
            findings_text=["Pneumothorax"],
            impression="Pneumothorax"
        )
        assert len(case.differential_diagnosis) > 0
