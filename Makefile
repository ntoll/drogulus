XARGS := xargs -0 $(shell test $$(uname) = Linux && echo -r)
GREP_T_FLAG := $(shell test $$(uname) = Linux && echo -T)

all:
	@echo "\nThere is no default Makefile target right now."
	@echo "Try:\n"
	@echo "make clean - reset the project and remove auto-generated assets."
	@echo "make pyflakes - run the PyFlakes code checker."
	@echo "make pep8 - run the PEP8 style checker."
	@echo "make test - run the test suite."
	@echo "make check - run all the checkers and tests."
	@echo "make docs - run sphinx to create project documentation."
	@echo "make web - build the project website."

clean:
	rm -rf dist docs/_build website/site/docs website/site/*.html
	find . \( -name '*.py[co]' -o -name dropin.cache \) -print0 | $(XARGS) rm
	find . \( -name '*.tgz' -o -name dropin.cache \) -print0 | $(XARGS) rm
	find . -name _trial_temp -type d -print0 | $(XARGS) rm -r

pyflakes:
	find . \( -name _build -o -name var \) -type d -prune -o -name '*.py' -print0 | $(XARGS) pyflakes

pep8:
	find . \( -name _build -o -name var \) -type d -prune -o -name '*.py' -print0 | $(XARGS) -n 1 pep8 --repeat

test: clean
	trial --rterrors --coverage test
	@echo "\nMissing test coverage:"
	@cd _trial_temp/coverage; grep -n $(GREP_T_FLAG) '>>>>>' drogulus.*

check: pep8 pyflakes test

docs: clean
	$(MAKE) -C docs html
	@echo "\nDocumentation can be viewed in your browser here:"
	@echo file://`pwd`/docs/_build/html/index.html
	@echo "\n"
	rm -rf website/site/docs
	cp -r `pwd`/docs/_build/html website/site/docs

web: docs
	@echo "\nGenerating static pages from templates..."
	python website/build.py
	tar cfvz deployable_website.tgz -C website/site/ .
	@echo "\nDone!"
