PYTHON ?= python3
.PHONY: test demo check
test:
	$(PYTHON) -m unittest discover -s tests -v
demo:
	$(PYTHON) -m careloop demo
check: test demo
	$(PYTHON) -m compileall -q careloop
