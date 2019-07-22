# ---------------------------------------------------------
# Test targets
# ---------------------------------------------------------

.PHONY: test
test:
	@pytest --cov=galaxy_importer --cov-branch

.PHONY: test/flake8
test/flake8:
	@flake8 galaxy_importer tests
