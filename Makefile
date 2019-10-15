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
	rm galaxy_importer/*,cover; rm galaxy_importer/utils/*,cover

.PHONY: test/flake8
test/flake8:
	@flake8 --max-line-length=99 galaxy_importer tests
