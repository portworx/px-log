.PHONY: install clean distclean

all: venv/dist/px-log

venv:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

venv/dist/px-log: venv
	cd ./venv && ./bin/pyinstaller --onefile ../px-log.py

install: venv/dist/px-log
	install -o root -g root -m 755 -t /usr/local/bin $<

clean:
	rm -f venv/dist/px-log

distclean: clean
	rm -fr venv __pycache__
