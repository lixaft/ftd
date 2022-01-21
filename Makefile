# Run all command
.PHONY: all
all:
	make docs tests line

# Build the sphinx documentation
.PHONY: docs
docs:
	sphinx-build docs/ docs/_build/ -vE

# Run the tests in maya
.PHONY: tests
tests:
	mayapy run_tests.py

# Run pre-commit in the repository
.PHONY: lint
lint:
	pre-commit run -a

# Clear all the unecessary file.
.PHONY: clean
clean:
	@find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
	@rm -f .coverage
	@rm -rf                  \
		build/              \
		dist/               \
		cover/              \
		htmlcov/            \
		.temp/              \
		.tox/               \
		.vscode/            \
		.mypy_cache/        \
		.pytest_cache/      \
		docs/_build/        \
		src/ftd.egg-info    \
