# CXR Multimodal Report Grounder

### [Open the Live Application →](https://abusuraihsakhri.github.io/cxr-multimodal-report-grounder/)

A Python research toolkit and static browser demonstration for chest radiograph report terminology, approximate anatomical-region templates, heuristic report comparison, and teaching-case generation.

**Scope and limitations:** This project does **not** interpret image pixels. Template bounding boxes are fixed normalized coordinates; they are not measured disease locations, trained-model attention, or diagnostic predictions. No clinical validation or calibrated confidence is established. Do not use for clinical decisions.

## Browser application

The web/ application runs entirely in a modern browser. It accepts a de-identified study ID, one finding statement per line, and an optional local PNG/JPEG/WebP image (20 MB maximum). It displays approximate anatomical templates, distinguishes explicitly negated statements from positive findings, and exports JSON annotations. The uploaded image is rendered locally using an object URL and is not sent to a server. DICOM input is not supported in the browser.

To preview it locally:

~~~bash
python -m http.server 8001 --directory web
# Open http://localhost:8001/
~~~

The browser application is deployed through GitHub Pages using the GitHub Actions workflow. The deployment job verifies that the published HTML and JavaScript assets are accessible.

## Python setup

Python 3.10–3.12 is exercised in CI. Python 3.9+ is declared by the package.

~~~bash
git clone https://github.com/abusuraihsakhri/cxr-multimodal-report-grounder.git
cd cxr-multimodal-report-grounder
python -m pip install -e '.[test]'
pytest -q
node --test web/grounding.test.mjs
~~~

Create a strong audit key when running the Python service:

~~~bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python cli.py serve --host 127.0.0.1 --port 8000
# Open http://127.0.0.1:8000/ to reach /web/
~~~

The FastAPI server provides GET /health, GET /metrics, POST /api/audit, POST /api/chat, GET /api/audit/logs, and serves the static browser frontend at /web/.

CLI examples:

~~~bash
python cli.py audit --task-id STUDY-001 --target TEST-001 --primary 28.5 --secondary 14.2
python cli.py batch -i sample.csv -o results.csv
python cli.py verify-audit
python simulator.py 100
~~~

The cxr_grounder/ Python package separately contains VisualGroundingEngine, DiscrepancyDetector, and TeachingFileGenerator for keyword-based region assignment, text-similarity comparison, and synthetic teaching examples. The generic agents/ task-audit pipeline is not an image-analysis model. The installed console script targets cxr_grounder.cli; python cli.py invokes the separate generic audit interface.

## Security and data handling

- The static browser tool processes text and images locally without external API calls. JSON exports are created in the browser.
- Python auditing uses keyed HMAC-SHA256 signatures over chained audit record metadata. The in-memory log is not persistent across restarts.
- A regex-based identifier filter screens selected task fields, including nested attributes. **It is not comprehensive PHI detection or de-identification**; use synthetic/de-identified inputs only.
- The mock LLM implementation returns canned text. Selecting other provider names currently does not activate real remote inference.
- The FastAPI service has no authentication/authorization layer. Audit logs and metrics are not suitable for unprotected public deployment. Deploy behind access controls and TLS; do not use actual patient data.
- Docker Compose requires AUDIT_SECRET_KEY in the shell environment before startup: docker compose up --build.

## Tests and implementation

Python: Pydantic v2, FastAPI, uvicorn, standard-library data processing. Browser: native ES modules and SVG. CI runs pytest, Python compilation, audit integrity checks, and Node.js browser-mapping unit tests on Python 3.10, 3.11 and 3.12. Browser features use current Chromium, Firefox, or Safari with ES module support.

The repository has two distinct CLI paths (cli.py and cxr_grounder/cli.py); both are retained for compatibility. Further work is needed for clinically validated multimodal inference, secure server deployment, or DICOM processing.

## License

MIT — see [LICENSE](LICENSE).
