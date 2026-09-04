"""
Pytest configuration for cxr-multimodal-report-grounder tests.
Sets up required environment variables and test fixtures.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables before importing application modules
os.environ.setdefault("AUDIT_SECRET_KEY", "test-audit-secret-key-2026-min-16-chars")
