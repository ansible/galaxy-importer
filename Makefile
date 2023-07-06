# ---------------------------------------------------------
# Lint targets
# ---------------------------------------------------------

.PHONY: lint
lint:
	@black . --extend-exclude .github/ --line-length 100 --diff --check
	@flake8

.PHONY: lint/format/black
lint/format/black:
	@black . --extend-exclude .github/ --line-length 100


# ---------------------------------------------------------
# Test targets
# ---------------------------------------------------------

.PHONY: test
test: lint test/unit test/functional
	@echo "ALL MAKE TARGET TESTS SUCCESSFUL"

.PHONY: test/unit
test/unit:
	@pytest tests/unit --cov=galaxy_importer --cov-branch

.PHONY: test/unit/annotate
test/unit/annotate:
	@pytest tests/unit --cov=galaxy_importer --cov-branch --cov-report annotate

.PHONY: test/unit/annotate/clean
test/unit/annotate/clean:
	find galaxy_importer -type f -name '*,cover' -delete

.PHONY: test/functional
test/functional:
	@sh tests/functional/*

.PHONY: test/integration
test/integration:
	@pytest tests/integration -v
