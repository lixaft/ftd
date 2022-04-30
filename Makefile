.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target] ...'
	@echo
	@echo 'Targets:'
	@grep -E '^\w+:\s##\s.+' $(MAKEFILE_LIST) |  awk 'BEGIN {FS = ":.*## "}; {printf "  %-15s %s\n", $$1, $$2}'


.PHONY: docs
docs: ## Build sphinx documentation
	@python scripts/build_docs.py

.PHONY: tests
tests: ## Run the tests in maya
	@python scripts/run_tests.py -v

.PHONY: lint
lint: ## Run pre-commit in the repository
	@pre-commit run -a

.PHONY: clean
clean: ## Delete all the unecessary file.
	@rm -f .coverage
	@rm -rf \
		build/ \
		dist/ \
		htmlcov/ \
		.temp/ \
		.vscode/ \
		.mypy_cache/ \
		.pytest_cache/ \
		docs/build/ \
		docs/source/apigen \
		src/ftd.egg-info
