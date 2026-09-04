"""
Tests for input validation and security enhancements.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.models import SystemTaskPayload
from agents.base import PHIGuard, SecurityException, AuditTrail


class TestInputValidation:
    def test_valid_task_id(self):
        p = SystemTaskPayload(
            task_id="TASK-2026-001",
            target_identifier="KEY-01",
            primary_metric=10.0
        )
        assert p.task_id == "TASK-2026-001"

    def test_invalid_task_id_special_chars(self):
        with pytest.raises(ValueError, match="Identifier must be"):
            SystemTaskPayload(
                task_id="TASK 001",  # space not allowed
                target_identifier="KEY-01",
                primary_metric=10.0
            )

    def test_invalid_task_id_path_traversal(self):
        with pytest.raises(ValueError, match="Identifier must be"):
            SystemTaskPayload(
                task_id="../../../etc/passwd",
                target_identifier="KEY-01",
                primary_metric=10.0
            )

    def test_invalid_task_id_too_long(self):
        with pytest.raises(ValueError, match="Identifier must be"):
            SystemTaskPayload(
                task_id="A" * 65,
                target_identifier="KEY-01",
                primary_metric=10.0
            )

    def test_invalid_metric_nan(self):
        with pytest.raises(ValueError, match="NaN"):
            SystemTaskPayload(
                task_id="TASK-01",
                target_identifier="KEY-01",
                primary_metric=float("nan")
            )

    def test_invalid_metric_inf(self):
        with pytest.raises(ValueError, match="finite"):
            SystemTaskPayload(
                task_id="TASK-01",
                target_identifier="KEY-01",
                primary_metric=float("inf")
            )

    def test_invalid_metric_too_large(self):
        with pytest.raises(ValueError, match="between"):
            SystemTaskPayload(
                task_id="TASK-01",
                target_identifier="KEY-01",
                primary_metric=1e7
            )

    def test_valid_metrics(self):
        p = SystemTaskPayload(
            task_id="TASK-01",
            target_identifier="KEY-01",
            primary_metric=100.0,
            secondary_metric=-50.0
        )
        assert p.primary_metric == 100.0
        assert p.secondary_metric == -50.0


class TestPHIGuard:
    def test_clean_text_passes(self):
        PHIGuard.assert_no_phi("Normal specimen KEY-001 within parameters")

    def test_mrn_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-12345678")

    def test_ssn_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_phone_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call 555-123-4567")

    def test_email_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Email: patient@example.com")

    def test_dob_blocked(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("DOB: 01/15/1985")

    def test_redact_phi(self):
        redacted = PHIGuard.redact_phi("Patient MRN-12345678 has condition")
        assert "MRN-12345678" not in redacted
        assert "[REDACTED_IDENTIFIER]" in redacted


class TestAuditTrailSecurity:
    def test_audit_trail_requires_key_or_env(self):
        # Should work because conftest.py sets AUDIT_SECRET_KEY
        trail = AuditTrail()
        assert trail.secret_key is not None

    def test_audit_trail_rejects_short_key(self):
        with pytest.raises(SecurityException, match="at least 16 characters"):
            AuditTrail(secret_key="short")

    def test_audit_trail_accepts_valid_key(self):
        trail = AuditTrail(secret_key="this-is-a-valid-key-1234567890")
        assert len(trail.secret_key) > 0
