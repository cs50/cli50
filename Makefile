PREFIX = /usr/local

.PHONY: all
all: cli50

cli50:

.PHONY: install
install: cli50
	mkdir -p ${DESTDIR}${PREFIX}/bin
	cp -f cli50 ${DESTDIR}${PREFIX}/bin
	chmod 755 ${DESTDIR}${PREFIX}/bin/cli50

.PHONY: uninstall
uninstall:
	rm -f ${DESTDIR}${PREFIX}/bin/cli50
