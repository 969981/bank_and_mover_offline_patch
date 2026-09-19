.PHONY: all clean verify FORCE host-test

export MSYS2_ARG_CONV_EXCL := *

ifeq ($(strip $(DEVKITARM)),)
$(error DEVKITARM is not set; export DEVKITARM=/path/to/devkitARM)
endif

TARGET_ROOT := ..
TOOLS := $(TARGET_ROOT)/tools
ARMIPS ?= $(TOOLS)/armips/armips
IPS_TOOL ?= $(TOOLS)/flips/flips
PYTHON ?= python3
BUILD := $(TARGET_ROOT)/build
TITLE_ID := 00040000000C9B00
BASE := $(TARGET_ROOT)/rom/exefs/00040000000C9B00.dec.code
PATCHED := $(BUILD)/00040000000C9B00.dec.code
RELEASE_ROOT := $(TARGET_ROOT)/../release
RELEASE_TITLE := $(RELEASE_ROOT)/$(TITLE_ID)
RELEASE_IPS := $(RELEASE_TITLE)/code.ips
RUNTIME_OBJECT := $(BUILD)/official_bulk_sync.o
CORE_OBJECT := $(BUILD)/official_bulk_sync_core.o
SYMBOLS := $(BUILD)/official-armips-symbols.txt

CC := $(DEVKITARM)/bin/arm-none-eabi-gcc
CFLAGS := -std=c11 -Os -march=armv6k -mtune=mpcore -marm -mfloat-abi=soft \
	-ffreestanding -fno-builtin -fno-stack-protector -fno-unwind-tables \
	-fno-asynchronous-unwind-tables -fomit-frame-pointer -fno-common \
	-ffunction-sections -fdata-sections -Wall -Wextra -Werror

all: $(RELEASE_IPS) verify

$(BUILD):
	mkdir -p "$@"

$(RUNTIME_OBJECT): official_bulk_sync.c official_bulk_sync.h | $(BUILD)
	"$(CC)" $(CFLAGS) -c "$<" -o "$@"

$(CORE_OBJECT): official_bulk_sync_core.c official_bulk_sync.h | $(BUILD)
	"$(CC)" $(CFLAGS) -DOFFICIAL_BULK_RUNTIME -c "$<" -o "$@"

$(PATCHED): FORCE main_official.s $(RUNTIME_OBJECT) $(CORE_OBJECT) $(BASE)
	"$(ARMIPS)" -erroronwarning -stat -sym "$(SYMBOLS)" main_official.s

$(RELEASE_IPS): $(PATCHED)
	mkdir -p "$(dir $@)"
	rm -f "$@"
	"$(IPS_TOOL)" --create --ips "$(BASE)" "$(PATCHED)" "$@"

host-test:
	$(CC_FOR_BUILD) -std=c11 -O2 -Wall -Wextra -Werror official_bulk_sync_host_test.c official_bulk_sync_core.c -o "$(BUILD)/official_bulk_sync_host_test"
	"$(BUILD)/official_bulk_sync_host_test"

verify: $(PATCHED) $(RELEASE_IPS) verify_official_bulk_sync.py
	"$(PYTHON)" verify_official_bulk_sync.py --base "$(BASE)" --patched "$(PATCHED)" --symbols "$(SYMBOLS)" --ips "$(RELEASE_IPS)"

clean:
	rm -rf "$(RELEASE_TITLE)" "$(BUILD)"

FORCE:
