.PHONY: all clean verify FORCE

export MSYS2_ARG_CONV_EXCL := *

ifeq ($(strip $(DEVKITARM)),)
$(error DEVKITARM is not set; export DEVKITARM=/path/to/devkitARM)
endif

TARGET_ROOT := ../..
TOOLS := $(TARGET_ROOT)/tools
ARMIPS ?= $(TOOLS)/armips/armips
IPS_TOOL ?= $(TOOLS)/flips/flips
PYTHON ?= python3
BUILD := $(TARGET_ROOT)/build/3-combine_patch
TITLE_ID := 00040000000C9B00
BASE := $(TARGET_ROOT)/00040000000C9B00.code
PATCHED := $(BUILD)/00040000000C9B00.code
RELEASE_TITLE := $(TARGET_ROOT)/release/3-combine_patch/luma/titles/$(TITLE_ID)
RELEASE_IPS := $(RELEASE_TITLE)/code.ips
RELEASE_ROMFS := $(RELEASE_TITLE)/romfs
ROMFS_SOURCE ?= ../../../../3ds_headless_ghidra/bank_base_v6_8_0/romfs
OBJECT := $(BUILD)/combine_patch.o
DISASSEMBLY := $(BUILD)/combine_patch.disasm.txt
SYMBOLS := $(BUILD)/armips-symbols.txt

CC := $(DEVKITARM)/bin/arm-none-eabi-gcc
OBJDUMP := $(DEVKITARM)/bin/arm-none-eabi-objdump
CFLAGS := -std=c11 -Os -march=armv6k -mtune=mpcore -marm -mfloat-abi=soft \
	-ffreestanding -fno-builtin -fno-stack-protector -fno-unwind-tables \
	-fno-asynchronous-unwind-tables -fomit-frame-pointer -fno-common \
	-ffunction-sections -fdata-sections -Wall -Wextra -Werror

all: $(RELEASE_IPS) layeredfs verify

$(BUILD):
	mkdir -p "$@"

$(OBJECT): combine_patch.c ../2-offline_patch/offline_patch.c | $(BUILD)
	"$(CC)" $(CFLAGS) -c "$<" -o "$@"
	"$(OBJDUMP)" -dr -z "$@" > "$(DISASSEMBLY)"

$(PATCHED): FORCE main.s $(OBJECT) $(BASE)
	"$(ARMIPS)" -erroronwarning -stat -sym "$(SYMBOLS)" main.s

$(RELEASE_IPS): $(PATCHED)
	mkdir -p "$(dir $@)"
	rm -f "$@"
	"$(IPS_TOOL)" --create --ips "$(BASE)" "$(PATCHED)" "$@"

layeredfs: patch_messages.py
	rm -rf "$(RELEASE_ROMFS)"
	"$(PYTHON)" patch_messages.py --source-romfs "$(ROMFS_SOURCE)" --output-romfs "$(RELEASE_ROMFS)"

verify: $(PATCHED) $(RELEASE_IPS) layeredfs verify_patch.py
	"$(PYTHON)" verify_patch.py --base "$(BASE)" --patched "$(PATCHED)" --symbols "$(SYMBOLS)" --ips "$(RELEASE_IPS)" --source-romfs "$(ROMFS_SOURCE)" --output-romfs "$(RELEASE_ROMFS)"

clean:
	rm -rf "$(RELEASE_TITLE)" "$(BUILD)"

FORCE:
