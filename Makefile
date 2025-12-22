# DevLens AI Makefile
# ===================
# Common development tasks

.PHONY: help test test-e2e demo-fast-stt install dev clean

# Default target
help:
	@echo "DevLens AI - Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all unit tests"
	@echo "  make test-e2e      - Run E2E pipeline tests"
	@echo ""
	@echo "Demo:"
	@echo "  make demo-fast-stt - Demo Fast STT on sample video"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev           - Start development server"
	@echo ""

# =============================================================================
# Testing
# =============================================================================

# Run all unit tests (excluding slow E2E)
test:
	python -m pytest tests/ --ignore=tests/test_e2e_flow.py --ignore=tests/test_e2e_pipeline.py -q --tb=short

# Run E2E pipeline tests
test-e2e:
	python -m pytest tests/test_e2e_pipeline.py -v --tb=short

# Run full test suite including E2E
test-all:
	python -m pytest tests/ -v --tb=short

# =============================================================================
# Demo
# =============================================================================

# Demo: Fast STT on sample video
# Creates a sample audio and transcribes it using faster-whisper
demo-fast-stt:
	@echo "=== Fast STT Demo ==="
	@echo "Testing local Whisper transcription..."
	python -c "\
from app.services.stt_fast_service import get_fast_stt_service, reset_fast_stt_service; \
reset_fast_stt_service(); \
stt = get_fast_stt_service(); \
print(f'STT Available: {stt.is_available}'); \
print(f'Model: {stt.model_size}'); \
status = stt.get_health_status(); \
print(f'Health: {status}');\
"
	@echo ""
	@echo "=== Demo Complete ==="

# =============================================================================
# Setup
# =============================================================================

# Install dependencies
install:
	pip install -r requirements.txt

# Start development server
dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Clean temporary files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf data/timelines/*.jsonl 2>/dev/null || true
	@echo "Cleaned temporary files"
