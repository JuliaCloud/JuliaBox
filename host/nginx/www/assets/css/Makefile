LESSC=lessc -x
LESS=base.less frames.less index.less
CSS=$(LESS:.less=.css)

less: $(CSS)

%.css: %.less
	$(LESSC) $< > $@
all: $(CSS)
