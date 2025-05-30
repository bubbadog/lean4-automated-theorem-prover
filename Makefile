# Lean 4 Automated Theorem Prover
# Author: Justin Karbowski
# Build system for three-agent theorem proving system

.PHONY: help install test test-single clean setup zip

help:
	@echo "Available commands:"
	@echo "  make setup     - Initial setup (install deps, create RAG DB)"
	@echo "  make install   - Install Python dependencies"
	@echo "  make test      - Run all tests"
	@echo "  make test-single TASK=task_id_0 - Run single test"
	@echo "  make clean     - Clean build artifacts"
	@echo "  make zip       - Create submission zip"

setup: install
	@echo "Setting up project..."
	python setup_config.py
	@echo "Creating sample task..."
	bash create_sample_task.sh
	@echo "Initializing RAG database..."
	python -c "from src.embedding_db import create_rag_database; create_rag_database()"
	@echo "✅ Setup complete!"
	@echo "Don't forget to add your OpenAI API key to .env"

install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

test:
	@echo "Running all tests..."
	python -m tests.tests

test-single:
	@echo "Running single test: $(TASK)"
	python -m tests.tests --task $(TASK)

clean:
	@echo "Cleaning build artifacts..."
	rm -rf __pycache__ src/__pycache__ tests/__pycache__
	rm -rf .pytest_cache
	rm -rf lean_playground/*.lean
	rm -rf .lake/build

zip:
	@echo "Creating submission zip..."
	zip -r submission.zip \
		src/ \
		tests/ \
		tasks/ \
		documents/ \
		embedding_db/ \
		lakefile.lean \
		Main.lean \
		requirements.txt \
		Makefile \
		README.md \
		architecture.md \
		.env.example \
		-x "*.pyc" "__pycache__/*" ".git/*" ".env"
	@echo "✅ Created submission.zip"

# Development helpers
dev-test:
	@echo "Running quick development test..."
	python -c "from src.main import main_workflow; print('✅ Import successful')"

validate-env:
	@echo "Validating environment..."
	@test -f .env || (echo "❌ .env file missing" && exit 1)
	@python -c "import openai; print('✅ OpenAI library available')"
	@lake --version > /dev/null || (echo "❌ Lake not available" && exit 1)
	@echo "✅ Environment validation passed"
