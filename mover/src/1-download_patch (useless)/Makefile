.PHONY: all clean FORCE

export MSYS2_ARG_CONV_EXCL := *

ifeq ($(strip $(DEVKITARM)),)
$(error DEVKITARM is not set; export DEVKITARM=/path/to/devkitARM)
endif

TARGET_ROOT := ../..
TOOLS := $(TARGET_ROOT)/tools
ARMIPS ?= $(TOOLS)/armips/armips
IPS_TOOL ?= $(TOOLS)/flips/flips
BUILD := $(TARGET_ROOT)/build/1-download_patch
TITLE_ID := 00040000000C9C00
BASE := $(TARGET_ROOT)/00040000000C9C00.code
PATCHED := $(BUILD)/00040000000C9C00.code
RELEASE_IPS := $(TARGET_ROOT)/release/1-download_patch/luma/titles/$(TITLE_ID)/code.ips
OBJECT := $(BUILD)/download_patch.o
DISASSEMBLY := $(BUILD)/download_patch.disasm.txt
SYMBOLS := $(BUILD)/armips-symbols.txt

CC := $(DEVKITARM)/bin/arm-none-eabi-gcc
OBJDUMP := $(DEVKITARM)/bin/arm-none-eabi-objdump

CFLAGS := -std=c11 -Os -march=armv6k -mtune=mpcore -marm -mfloat-abi=soft \
	-ffreestanding -fno-builtin -fno-stack-protector -fno-unwind-tables \
	-fno-asynchronous-unwind-tables -fomit-frame-pointer -fno-common \
	-ffunction-sections -fdata-sections -Wall -Wextra -Werror

all: $(RELEASE_IPS)

$(BUILD):
	mkdir -p "$@"

$(OBJECT): download_patch.c | $(BUILD)
	"$(CC)" $(CFLAGS) -c "$<" -o "$@"
	"$(OBJDUMP)" -dr -z "$@" > "$(DISASSEMBLY)"

$(PATCHED): FORCE main.s $(OBJECT) $(BASE)
	"$(ARMIPS)" -erroronwarning -stat -sym "$(SYMBOLS)" main.s

$(RELEASE_IPS): $(PATCHED)
	mkdir -p "$(dir $@)"
	rm -f "$@"
	"$(IPS_TOOL)" --create --ips "$(BASE)" "$(PATCHED)" "$@"

clean:
	rm -f "$(RELEASE_IPS)"
	rm -rf "$(BUILD)"

FORCE:
