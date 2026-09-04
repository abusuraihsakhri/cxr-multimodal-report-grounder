# CXR Multimodal Report Grounder

> **Domain:** Diagnostic Radiology & Medical Imaging AI
> **Reference Standards:** American College of Radiology (ACR), Fleischner Society, DICOM SR, CheXpert Labeling Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

CXR Multimodal Report Grounder is a medical AI system for chest X-Ray (CXR) analysis that:

- **Grounds radiological findings to image regions** - Links specific CXR findings (cardiomegaly, pleural effusion, etc.) to spatial bounding boxes on the image
- **Detects discrepancies** - Compares radiologist reports with AI findings to identify missed or overcalled findings
- **Generates teaching cases** - Creates annotated CXR teaching cases with quiz questions and differential diagnoses
- **Enforces zero-PHI outbound protection** - Blocks protected health information from leaving the system
- **Maintains tamper-evident audit trails** - HMAC-SHA256 chained cryptographic logs for every evaluation

---

## ⚙️ Key Capabilities & Algorithmic Modules

### Core Modules

| Module | Description |
|--------|-------------|
| `agents/` | Multi-agent orchestration with PHI guard, audit trail, and specialized workers |
| `cxr_grounder/` | Visual-language grounding engine, discrepancy detector, and teaching file generator |
| `enrichment.py` | Domain-specific enrichment engines for structured reporting and quality assurance |

### Specialized Workers

- **InvariantQCWorker** - Primary metric threshold monitoring and boundary auditing
- **SafetyEscalationWorker** - Critical safety interlock detection and emergency escalation
- **ProtocolConformanceWorker** - Specification conformance and anomaly triage

### Security & Compliance

- **Zero-PHI Outbound Interceptor** - AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers
- **HMAC-SHA256 Audit Trail** - Chained, cryptographically signed logs for every evaluation
- **Input Validation** - Strict bounds checking on all identifiers and metrics

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/cxr-multimodal-report-grounder.git
cd cxr-multimodal-report-grounder

# Install dependencies
pip install fastapi uvicorn pydantic pytest

# Set up environment variables
cp .env.example .env
# Edit .env and set your AUDIT_SECRET_KEY
```

---

## 🚀 Usage

### 1. Guided Interactive Mode
```bash
python cli.py audit
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 3. Batch CSV Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

### 4. System Chat
```bash
python cli.py chat "What standard is applied?"
```

### 5. Verify Audit Trail
```bash
python cli.py verify-audit
```

### 6. Launch REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference

| Parameter | Description | Default |
|:----------|:------------|:--------|
| `--task-id` | Unique task/case identifier (alphanumeric, hyphens, underscores) | TASK-2026-001 |
| `--target` | Target identifier | KEY-TARGET-01 |
| `--primary` | Primary measurement value (finite number) | 28.5 |
| `--secondary` | Secondary metric value (finite number) | 14.2 |
| `--critical` | Trigger critical escalation flag | False |
| `--status` | Status descriptor (e.g., NOMINAL, DISCORDANT) | DISCORDANT |

---

## 🔌 REST API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Service health check |
| `/metrics` | GET | Prometheus-compatible metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Query system configuration |
| `/api/audit/logs` | GET | Retrieve audit trail with integrity verification |

### Example API Request
```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "TASK-001",
    "target_identifier": "KEY-01",
    "primary_metric": 28.5,
    "secondary_metric": 14.2,
    "status_descriptor": "DISCORDANT",
    "is_critical_flag": true
  }'
```

---

## 🛡️ Security Architecture

### Environment Configuration

The system requires an `AUDIT_SECRET_KEY` environment variable for HMAC-SHA256 audit trail signing:

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Set in .env file
AUDIT_SECRET_KEY=your-secure-key-here-min-16-chars
```

### PHI Protection

The system actively blocks outbound PHI including:
- Medical Record Numbers (MRN)
- Social Security Numbers (SSN)
- Phone numbers
- Email addresses
- Dates of birth
- Patient names

### Input Validation

- Identifiers: 1-64 characters, alphanumeric/hyphen/underscore only
- Metrics: Finite numbers within bounded range (-1e6 to 1e6)
- Path traversal prevention on file operations

---

## 🧪 Testing

### Run All Tests
```bash
pytest -v
```

### Test Coverage

| Test File | Description |
|:----------|:------------|
| `tests/test_cxr_grounder.py` | Core agent and coordinator functionality |
| `tests/test_cxr_multimodal_report_grounder.py` | PHI guard, workers, and supervisor consensus |
| `tests/test_cxr_grounding.py` | Visual grounding, discrepancy detection, teaching cases |
| `tests/test_validation.py` | Input validation and security enhancements |
| `tests/test_enrichment.py` | Enrichment suite execution |

### Run Simulation Benchmark
```bash
python simulator.py 1000
```

---

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t cxr-multimodal-report-grounder .
docker run -p 8000:8000 --env-file .env cxr-multimodal-report-grounder
```

---

## 📁 Project Structure

```
cxr-multimodal-report-grounder/
├── agents/                      # Multi-agent orchestration
│   ├── api.py                   # FastAPI REST server
│   ├── base.py                  # PHI guard, audit trail, security
│   ├── models.py                # Pydantic data models with validation
│   ├── supervisor.py            # Master orchestrator
│   ├── workers.py               # Specialized domain workers
│   ├── llm_factory.py           # LLM provider abstraction
│   ├── learning.py              # Bayesian calibration engine
│   ├── metrics.py               # Prometheus metrics collector
│   └── streamer.py              # WebSocket telemetry broadcaster
├── cxr_grounder/                # Visual-language grounding
│   ├── models.py                # Frontier data models
│   ├── engine.py                # Core algorithmic engine
│   ├── agents.py                # Specialized sub-agents
│   ├── server.py                # FastAPI server factory
│   ├── cli.py                   # Command-line interface
│   ├── discrepancy_detector.py  # Radiology-AI comparison
│   ├── visual_grounding_engine.py  # Finding-to-region mapping
│   └── teaching_file_generator.py  # Teaching case generation
├── tests/                       # Test suite
├── web/                         # Operations console (HTML)
├── cli.py                       # Main CLI entry point
├── cxr_grounder_app.py          # Alternative CLI entry
├── simulator.py                 # High-throughput simulation
├── enrichment.py                # Domain enrichment engines
├── pyproject.toml               # Project configuration
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Container definition
└── .env.example                 # Environment template
```

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
