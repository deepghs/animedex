SPHINXOPTS    ?=
SPHINXBUILD   ?= $(shell which sphinx-build)
SOURCEDIR     ?= source
BUILDDIR      ?= build

.PHONY: help build html clean

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

build: html

html:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
	@touch "$(BUILDDIR)/html/.nojekyll"

clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
