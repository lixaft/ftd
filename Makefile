# run all command
.PHONY: all
all:
	make docs
	make tests
	make lint

# build the sphinx documentation
.PHONY: docs
docs:
	sphinx-build docs/ docs/_build/ -vE

# run the tests in maya
.PHONY: tests
tests:
	mayapy run_tests.py

# run pre-commit in the repository
.PHONY: lint
lint:
	pre-commit run -a

# clear all the unecessary file.
.PHONY: clean
clean:
	rm -f .coverage
	rm -rf                  \
		build/              \
		cover/              \
		dist/               \
		.temp/              \
		.tox/               \
		.vscode/            \
		.mypy_cache/        \
		pytest_cache/       \
		docs/_build/        \
		src/ftd.egg-info    \
