.PHONY: help package clean test unittest lint format docs rst_auto

PYTHON := $(shell which python)

PROJ_DIR     := .
DOC_DIR      := ${PROJ_DIR}/docs
DOC_SOURCE   := ${DOC_DIR}/source
BUILD_DIR    := ${PROJ_DIR}/build
DIST_DIR     := ${PROJ_DIR}/dist
TEST_DIR     := ${PROJ_DIR}/test
SRC_DIR      := ${PROJ_DIR}/animedex

RANGE_DIR        ?= .
RANGE_TEST_DIR   := ${TEST_DIR}/${RANGE_DIR}
RANGE_SRC_DIR    := ${SRC_DIR}/${RANGE_DIR}

COV_TYPES ?= xml term-missing

# RST documentation generation variables
PYTHON_CODE_DIR   := ${SRC_DIR}
RST_DOC_DIR       := ${DOC_SOURCE}/api_doc
PYTHON_CODE_FILES := $(shell find ${PYTHON_CODE_DIR} -name "*.py" ! -name "__*.py" 2>/dev/null)
RST_DOC_FILES     := $(patsubst ${PYTHON_CODE_DIR}/%.py,${RST_DOC_DIR}/%.rst,${PYTHON_CODE_FILES})
PYTHON_NONM_FILES := $(shell find ${PYTHON_CODE_DIR} -name "__init__.py" 2>/dev/null)
RST_NONM_FILES    := $(foreach file,${PYTHON_NONM_FILES},$(patsubst %/__init__.py,%/index.rst,$(patsubst ${PYTHON_CODE_DIR}/%,${RST_DOC_DIR}/%,$(patsubst ${PYTHON_CODE_DIR}/__init__.py,${RST_DOC_DIR}/index.rst,${file}))))

help:
	@echo "animedex Build System"
	@echo "====================="
	@echo ""
	@echo "Building and packaging:"
	@echo "  make package      Build sdist and wheel into dist/"
	@echo "  make clean        Remove build/, dist/, *.egg-info"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run pytest unit tests"
	@echo "                    Options: RANGE_DIR=<sub-path> COV_TYPES='xml term-missing'"
	@echo "                             MIN_COVERAGE=<percent> WORKERS=<n>"
	@echo "  make lint         Run flake8"
	@echo ""
	@echo "Documentation:"
	@echo "  make rst_auto     Regenerate docs/source/api_doc/*.rst from Python sources"
	@echo "                    Options: RANGE_DIR=<sub-path> to limit the scan"
	@echo "  make docs         Build the Sphinx HTML site (docs/build/html/)"
	@echo ""

package:
	$(PYTHON) -m build --sdist --wheel --outdir ${DIST_DIR}

clean:
	rm -rf ${DIST_DIR} ${BUILD_DIR} *.egg-info
	$(MAKE) -C "${DOC_DIR}" clean

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

# Aggregate target: regenerate all RST API docs from the source tree.
# RANGE_DIR can scope the run.
#
# The per-package "api_doc/<pkg>/index.rst" produced by `auto_rst.py`
# already carries the package-level toctree (and `.. automodule::`),
# so the docs entry point in `docs/source/index.rst` references
# `api_doc/index` directly. The standalone `auto_rst_top_index.py`
# script is kept in the repo for projects that ship multiple
# top-level Python packages; it is not part of the default pipeline.
rst_auto: ${RST_DOC_FILES} ${RST_NONM_FILES}
	@echo "rst_auto: regenerated $(words ${RST_DOC_FILES}) module rst(s) and $(words ${RST_NONM_FILES}) package rst(s)."

# Pattern rule: a flat module animedex/foo/bar.py -> docs/source/api_doc/foo/bar.rst
${RST_DOC_DIR}/%.rst: ${PYTHON_CODE_DIR}/%.py auto_rst.py Makefile
	@mkdir -p $(dir $@)
	$(PYTHON) auto_rst.py -i $< -o $@

# Pattern rule: a sub-package animedex/foo/__init__.py -> docs/source/api_doc/foo/index.rst
${RST_DOC_DIR}/%/index.rst: ${PYTHON_CODE_DIR}/%/__init__.py auto_rst.py Makefile
	@mkdir -p $(dir $@)
	$(PYTHON) auto_rst.py -i $< -o $@

# The top-level package: animedex/__init__.py -> docs/source/api_doc/index.rst
${RST_DOC_DIR}/index.rst: ${PYTHON_CODE_DIR}/__init__.py auto_rst.py Makefile
	@mkdir -p $(dir $@)
	$(PYTHON) auto_rst.py -i $< -o $@

docs:
	$(MAKE) -C "${DOC_DIR}" build
