LESSC=/usr/local/bin/lessc

LESS=base.less

CSS=$(LESS:.less=.css)

%.css: %.less
	$(LESSC) $< > $@

all: $(CSS)
