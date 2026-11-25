# Workshop demo and ADK 2.0 codelab: a multi-agent system (researcher, judge,
# content builder, orchestrator) over A2A, run locally or on Cloud Run.

CODELAB := codelab/building-a-multi-agent-system-adk2.md
TMP     ?= $(or $(TMPDIR),/tmp)/multi-agent-loop-docs

.PHONY: all help install lint test check docs run deploy clean

all: help

help:
	@echo "make install   pip install the demo's requirements into the python3 on PATH"
	@echo "make lint      ruff: our scripts in full, the vendored agents for errors only"
	@echo "make test      offline: compile, codelab code matches codelab-complete, docs/ is current"
	@echo "make check     lint and test"
	@echo "make docs      rebuild docs/ from the codelab markdown with claat"
	@echo "make run       start the five local services from codelab-complete (needs gcloud login)"
	@echo "make deploy    deploy codelab-complete to Cloud Run (uses the gcloud project)"
	@echo "make clean     remove __pycache__ and .ruff_cache"

install:
	python3 -m pip install -r codelab-complete/requirements.txt

# The agents and app are vendored from GoogleCloudPlatform/devrel-demos and carry
# upstream style findings, so they get errors only (E9, F). F401 and F541 are
# upstream too: the starter imports what attendees will use, and
# billing-enablement.py has a bare f-string. Reformatting them would create diffs
# that /sync-upstream has to reapply.
lint:
	ruff check scripts article
	ruff check --config codelab-complete/pyproject.toml --select E9,F --ignore F401,F541 codelab-complete codelab-starter
	@echo "lint OK"

# docs/ is generated; a fresh claat export must match it, apart from the two
# files added by hand for GitHub Pages (index.html redirect and .nojekyll).
test:
	python3 -m compileall -q codelab-complete codelab-starter scripts article
	python3 scripts/check_codelab.py $(CODELAB)
	rm -rf $(TMP) && mkdir -p $(TMP)
	claat export -o $(TMP) $(CODELAB)
	diff -r -x index.html -x .nojekyll $(TMP) docs
	rm -rf $(TMP)
	@echo "test OK"

check: lint test

docs:
	claat export -o docs $(CODELAB)

run:
	cd codelab-complete && ./run_local.sh

deploy:
	cd codelab-complete && ./deploy.sh

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .ruff_cache
