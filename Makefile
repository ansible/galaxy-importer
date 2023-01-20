# ---------------------------------------------------------
# Test targets
# ---------------------------------------------------------

.PHONY: test
test: test/lint test/unit test/integration
	@echo "ALL MAKE TARGET TESTS SUCCESSFUL"

.PHONY: test/lint
test/lint:
	@flake8
	@black . --extend-exclude .github/ --line-length 100 --check

.PHONY: test/unit
test/unit:
	@pytest tests/unit --cov=galaxy_importer --cov-branch --ignore=tests/unit/test_builder_local_image.py

.PHONY: test/unit/annotate
test/unit/annotate:
	@pytest tests/unit --cov=galaxy_importer --cov-branch --cov-report annotate

.PHONY: test/unit/annotate/clean
test/unit/annotate/clean:
	find galaxy_importer -type f -name '*,cover' -delete

.PHONY: test/integration
test/integration:
	@sh tests/integration/*
