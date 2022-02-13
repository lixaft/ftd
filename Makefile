# Run all command
.PHONY: all
all:
	@make docs tests lint

# Build the sphinx documentation
.PHONY: docs
docs:
	@python scripts/build_docs.py

# Run the tests in maya
.PHONY: tests
tests:
	@mayapy scripts/run_tests.py

# Run pre-commit in the repository
.PHONY: lint
lint:
	@pre-commit run -a

# Clear all the unecessary file.
.PHONY: clean
clean:
	@rm -f .coverage
	@rm -rf \
		build/ \
		dist/ \
		cover/ \
		htmlcov/ \
		.temp/ \
		.tox/ \
		.vscode/ \
		.mypy_cache/ \
		.pytest_cache/ \
		docs/_build/ \
		src/ftd.egg-info
