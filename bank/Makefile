PATCHES := 1-download_patch 2-offline_patch 3-upload_patch

.PHONY: all clean $(PATCHES) $(addprefix clean-,$(PATCHES))

all: $(PATCHES)

1-download_patch:
	$(MAKE) -C src/1-download_patch all

2-offline_patch:
	$(MAKE) -C src/2-offline_patch all

3-upload_patch:
	$(MAKE) -C src/3-upload_patch all

clean: $(addprefix clean-,$(PATCHES))

clean-1-download_patch:
	$(MAKE) -C src/1-download_patch clean

clean-2-offline_patch:
	$(MAKE) -C src/2-offline_patch clean

clean-3-upload_patch:
	$(MAKE) -C src/3-upload_patch clean
