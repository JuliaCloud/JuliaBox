LESSC=lessc -x
LESS=base.less frames.less
CSS=$(LESS:.less=.css)

less: $(CSS)

%.css: %.less
	$(LESSC) $< > $@
all: $(CSS)
