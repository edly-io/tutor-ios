.DEFAULT_GOAL := help
.PHONY: docs
SRC_DIRS = ./ios ./tests
# Path to a local openedx-app-ios checkout, for the Xcode build check.
APP_DIR ?=

# Warning: These checks are not necessarily run on every PR.
test: test-lint test-types test-format test-unit  # Run all static checks and unit tests.

test-unit: ## Run unit tests
	python -m pytest tests/

test-build-config: ## Verify the generated config against the real iOS app (no Xcode needed)
	./tests/test_build_config.sh

test-build-xcode: ## Check whether this machine can compile the iOS app
	./tests/test_build_xcode.sh $(APP_DIR)

test-format: ## Run code formatting tests
	ruff format --check --diff ${SRC_DIRS}

test-lint: ## Run code linting tests
	ruff check ${SRC_DIRS}

test-types: ## Run type checks.
	mypy --exclude=templates --ignore-missing-imports --implicit-reexport --strict ${SRC_DIRS}

format: ## Format code
	ruff format ${SRC_DIRS}

fix-lint: ## Fix lint errors automatically
	ruff check --fix ${SRC_DIRS}

changelog-entry: ## Create a new changelog entry.
	scriv create

changelog: ## Collect changelog entries in the CHANGELOG.md file.
	scriv collect

version: ## Print the current tutor-ios version
	@python -c 'import io, os; about = {}; exec(io.open(os.path.join("ios", "__about__.py"), "rt", encoding="utf-8").read(), about); print(about["__version__"])'

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'
