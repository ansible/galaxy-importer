# ---------------------------------------------------------
# Test targets
# ---------------------------------------------------------

.PHONY: test
test:
	@pytest --cov=galaxy_importer --cov-branch

.PHONY: test/flake8
test/flake8:
	@flake8 --max-line-length=99 galaxy_importer tests
