"""Security, clinical-text, API, and integration regressions."""
import pytest
from fastapi.testclient import TestClient

from agents.base import AuditTrail, SecurityException
from agents.api import app
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cxr_grounder.discrepancy_detector import DiscrepancyDetector, DiscrepancyType
from cxr_grounder.visual_grounding_engine import VisualGroundingEngine, GroundingConfidence


def test_audit_signature_tampering_detected():
    trail = AuditTrail(secret_key="test-key-with-sufficient-length")
    trail.log("test", "qa", "EXAMPLE", {"status": "ok"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "modified"
    assert not trail.verify_integrity()


def test_audit_payload_hash_tampering_detected():
    trail = AuditTrail(secret_key="test-key-with-sufficient-length")
    trail.log("test", "qa", "EXAMPLE", {"status": "ok"})
    trail.logs[0]["payload_hash"] = "0" * 64
    assert not trail.verify_integrity()


def test_audit_missing_field_does_not_crash():
    trail = AuditTrail(secret_key="test-key-with-sufficient-length")
    trail.log("test", "qa", "EXAMPLE", {"status": "ok"})
    del trail.logs[0]["current_hash"]
    assert not trail.verify_integrity()


def test_negated_and_positive_observations_are_not_concordant():
    report = DiscrepancyDetector.compare_findings(
        ["No pneumothorax"], ["Pneumothorax"], similarity_threshold=0.55
    )
    assert report.concordant_count == 0
    assert report.missed_count == 1
    assert report.overcalled_count == 1


def test_laterality_disagreement_is_not_concordant():
    report = DiscrepancyDetector.compare_findings(
        ["Right pleural effusion"], ["Left pleural effusion"]
    )
    assert report.concordant_count == 0
    assert any(x.discrepancy_type == DiscrepancyType.LATERALITY_MISMATCH
               for x in report.discrepancies)


def test_pleural_text_maps_to_costophrenic_template():
    item = VisualGroundingEngine.ground_finding("Right pleural effusion")
    assert item.location_anatomy == "right_costophrenic_angle"


def test_negated_finding_has_no_claimed_confidence():
    item = VisualGroundingEngine.ground_finding("No pneumothorax")
    assert item.grounding_confidence == GroundingConfidence.UNCERTAIN
    assert item.bounding_box.confidence == 0.0


def test_metadata_is_screened_for_obvious_identifiers():
    supervisor = SystemSupervisor()
    payload = SystemTaskPayload(
        task_id="TASK-1", target_identifier="KEY-1", primary_metric=1.0,
        attributes={"note": "Patient MRN-123456"}
    )
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)


def test_web_console_served_locally():
    client = TestClient(app)
    assert client.get("/", follow_redirects=False).status_code in (301, 302, 307, 308)
    page = client.get("/web/")
    assert page.status_code == 200
    assert "template" in page.text.lower()
    assert client.get("/web/grounding.mjs").status_code == 200


def test_api_rejects_sensitive_identifier_without_server_error():
    client = TestClient(app)
    response = client.post("/api/audit", json={
        "task_id": "TASK-1", "target_identifier": "KEY-1",
        "primary_metric": 1.0, "secondary_metric": 0.0,
        "attributes": {"note": "Patient MRN-123456"}
    })
    assert response.status_code == 422
    assert "MRN-123456" not in response.text


def test_successful_audit_updates_counters():
    client = TestClient(app)
    before = client.get("/metrics").text
    response = client.post("/api/audit", json={
        "task_id": "TASK-COUNTER-1", "target_identifier": "KEY-1",
        "primary_metric": 1.0, "secondary_metric": 0.0,
        "status_descriptor": "NOMINAL",
    })
    assert response.status_code == 200
    assert "ROUTINE" in response.json()["overall_urgency"]
    assert client.get("/metrics").text != before


def test_streamer_importable():
    import agents.streamer
    assert hasattr(agents.streamer, "GLOBAL_STREAMER")

def test_unknown_finding_not_counted_as_grounded():
    item = VisualGroundingEngine.ground_finding("Unmapped nonspecific statement")
    assert item.grounding_confidence == GroundingConfidence.UNCERTAIN
    assert item.location_anatomy == "unmatched"
    assert item.bounding_box.area == 0


def test_bilateral_effusion_covers_both_sides():
    item = VisualGroundingEngine.ground_finding("Bilateral pleural effusion")
    assert item.bounding_box.x_min == 0.10
    assert item.bounding_box.x_max == 0.90
