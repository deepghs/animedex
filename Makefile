.PHONY: help package clean test unittest lint format docs

PYTHON := $(shell which python)

PROJ_DIR     := .
DOC_DIR      := ${PROJ_DIR}/docs
BUILD_DIR    := ${PROJ_DIR}/build
DIST_DIR     := ${PROJ_DIR}/dist
TEST_DIR     := ${PROJ_DIR}/test
SRC_DIR      := ${PROJ_DIR}/animedex

RANGE_DIR        ?= .
RANGE_TEST_DIR   := ${TEST_DIR}/${RANGE_DIR}
RANGE_SRC_DIR    := ${SRC_DIR}/${RANGE_DIR}

COV_TYPES ?= xml term-missing

help:
	@echo "animedex Build System"
	@echo "====================="
	@echo ""
	@echo "  make package   - Build sdist and wheel into dist/"
	@echo "  make clean     - Remove build/, dist/, *.egg-info"
	@echo "  make test      - Run pytest unit tests"
	@echo "  make lint      - Run flake8"
	@echo ""

package:
	$(PYTHON) -m build --sdist --wheel --outdir ${DIST_DIR}

clean:
	rm -rf ${DIST_DIR} ${BUILD_DIR} *.egg-info

test: unittest

unittest:
	UNITTEST=1 \
		pytest "${RANGE_TEST_DIR}" \
		-sv -m unittest \
		$(shell for type in ${COV_TYPES}; do echo "--cov-report=$$type"; done) \
		--cov="${RANGE_SRC_DIR}" \
		$(if ${MIN_COVERAGE},--cov-fail-under=${MIN_COVERAGE},) \
		$(if ${WORKERS},-n ${WORKERS},)

lint:
	flake8 ${SRC_DIR} ${TEST_DIR}

docs:
	@echo "docs target is reserved; sphinx scaffolding is not yet committed."
