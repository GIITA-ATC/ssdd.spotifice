# Activate .venv if it exists
ACTIVATE := $(if $(wildcard .venv/bin/activate),. .venv/bin/activate &&,)

.PHONY: check-slice test clean distclean

check-slice:  check-spotifice_v0.ice

check-%.ice: %.ice
	slice2html -I /usr/share/ice/slice $< --output-dir /tmp

test:
	clear
	$(ACTIVATE) for t in test/test_*.py; do \
		pytest -v $$t || exit 1; \
	done

media: portal2-ost.zip
	mkdir -p media
	unzip -o $< -d media

portal2-ost.zip:
	wget http://media.steampowered.com/apps/portal2/soundtrack/Portal2-OST-Complete.zip -O $@

run-%: media_%.py %.config
	$(ACTIVATE) python3 $< --Ice.Config=$(word 2,$^)

clean:
	$(RM) -r Spotifice spotifice*.py *.html __pycache__ .pytest_cache

distclean: clean
	$(RM) -r media .venv portal2-ost.zip
