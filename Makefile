.PHONY: help package clean test unittest lint format format-check docs rst_auto build build_info build_info_clean test_cli

PYTHON := $(shell which python)

PROJ_DIR        := .
DOC_DIR         := ${PROJ_DIR}/docs
DOC_SOURCE      := ${DOC_DIR}/source
BUILD_DIR       := ${PROJ_DIR}/build
DIST_DIR        := ${PROJ_DIR}/dist
TEST_DIR        := ${PROJ_DIR}/test
SRC_DIR         := ${PROJ_DIR}/animedex
TOOLS_DIR       := ${PROJ_DIR}/tools
BUILD_INFO_FILE := ${SRC_DIR}/config/build_info.py

# PyInstaller output. Windows adds the .exe suffix; honour ${IS_WIN} when
# CI sets it, otherwise infer from the operating system.
ifeq ($(OS),Windows_NT)
PYINSTALLER_BIN := ${DIST_DIR}/animedex.exe
else
PYINSTALLER_BIN := ${DIST_DIR}/animedex
endif

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
	@echo "  make package         Build sdist and wheel into dist/"
	@echo "  make build           Build a standalone PyInstaller binary into dist/"
	@echo "                       (depends on build_info; auto-runs it first)"
	@echo "  make build_info      Regenerate animedex/config/build_info.py from git state"
	@echo "  make build_info_clean Remove the generated build_info.py"
	@echo "  make clean           Remove build/, dist/, *.egg-info, .spec, doc build/"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run pytest unit tests (regression suite)"
	@echo "                       Options: RANGE_DIR=<sub-path> COV_TYPES='xml term-missing'"
	@echo "                                MIN_COVERAGE=<percent> WORKERS=<n>"
	@echo "  make test_cli        Run the post-build subprocess smoke-test against dist/animedex"
	@echo "  make lint            Run flake8"
	@echo "  make format          Reformat source + tests with ruff (line-length 120)"
	@echo "  make format-check    Verify formatting without modifying files (CI use)"
	@echo ""
	@echo "Documentation:"
	@echo "  make rst_auto        Regenerate docs/source/api_doc/*.rst from Python sources"
	@echo "                       Options: RANGE_DIR=<sub-path> to limit the scan"
	@echo "  make docs            Build the Sphinx HTML site (docs/build/html/)"
	@echo ""

# Build sdist + wheel. The build_info module is regenerated first so
# the resulting distribution carries the same per-build metadata that
# the PyInstaller binary does. MANIFEST.in lists the file explicitly,
# because it is .gitignore'd and would otherwise be omitted from the
# sdist.
package: build_info
	$(PYTHON) -m build --sdist --wheel --outdir ${DIST_DIR}

# (Re-)generate the per-build metadata module from the working tree's
# git state. The output file (animedex/config/build_info.py) is
# .gitignore'd and consumed by animedex.config.buildmeta. The package
# functions whether or not this file exists.
build_info:
	$(PYTHON) tools/generate_build_info.py -o ${BUILD_INFO_FILE}

build_info_clean:
	rm -f ${BUILD_INFO_FILE}

# Build a single-file standalone binary using PyInstaller via a generated
# spec file (tools/generate_spec.py + tools/resources.py). The spec
# captures excludes, hidden imports, and the data manifest, so future
# bundled assets are picked up without changing this target. build_info
# runs first so animedex/config/build_info.py is on disk when the spec
# is rendered (it is listed in HIDDEN_IMPORTS) and PyInstaller can
# include it in the bundle.
build: build_info
	$(PYTHON) -m tools.generate_spec -o animedex.spec
	$(PYTHON) -m PyInstaller animedex.spec --noconfirm --clean
	@echo "Built: ${PYINSTALLER_BIN}"

# Subprocess-based smoke test of the freshly built binary. Imports nothing
# from the project at runtime; uses tools/test_cli.py as a stdlib-only
# harness so the same script can run on the build host or in CI.
test_cli:
	$(PYTHON) -m tools.test_cli ${PYINSTALLER_BIN}

clean: build_info_clean
	rm -rf ${DIST_DIR} ${BUILD_DIR} *.egg-info animedex.spec
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

# Reformat the tree in place (intended pre-commit hook).
format:
	ruff format ${SRC_DIR} ${TEST_DIR}
	ruff check --fix ${SRC_DIR} ${TEST_DIR}

# Verify formatting without modifying anything; suitable for CI.
format-check:
	ruff format --check ${SRC_DIR} ${TEST_DIR}
	ruff check ${SRC_DIR} ${TEST_DIR}

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
