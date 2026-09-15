PATCHES := 3-combine_patch

.PHONY: all clean $(PATCHES) $(addprefix clean-,$(PATCHES))

all: $(PATCHES)

3-combine_patch:
	$(MAKE) -C src/3-combine_patch all

clean: $(addprefix clean-,$(PATCHES))

clean-3-combine_patch:
	$(MAKE) -C src/3-combine_patch clean
