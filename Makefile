# ---------------------------------------------------------
# Lint targets
# ---------------------------------------------------------

.PHONY: lint
lint:
	black . --diff --check
	flake8
	ruff check

.PHONY: lint/format/black
lint/format/black:
	black .


# ---------------------------------------------------------
# Test targets
# ---------------------------------------------------------

.PHONY: test
test: lint test/unit test/functional
	@echo "ALL MAKE TARGET TESTS SUCCESSFUL"

.PHONY: test/unit
test/unit:
	pytest tests/unit --cov=galaxy_importer --cov-config=pyproject.toml --cov-report xml:coverage.xml

.PHONY: test/unit/annotate
test/unit/annotate:
	pytest tests/unit --cov=galaxy_importer --cov-config=pyproject.toml --cov-report annotate

.PHONY: test/unit/annotate/clean
test/unit/annotate/clean:
	find galaxy_importer -type f -name '*,cover' -delete

.PHONY: test/integration
test/integration:
	pytest tests/integration -v
