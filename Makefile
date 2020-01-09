# ---------------------------------------------------------
# Test targets
# ---------------------------------------------------------

.PHONY: test
test:
	@pytest --cov=galaxy_importer --cov-branch

.PHONY: test/annotate
test/annotate:
	@pytest --cov=galaxy_importer --cov-branch --cov-report annotate

.PHONY: test/annotate/clean
test/annotate/clean:
	find galaxy_importer -type f -name '*,cover' -delete

.PHONY: test/flake8
test/flake8:
	@flake8 --max-line-length=99 galaxy_importer tests
