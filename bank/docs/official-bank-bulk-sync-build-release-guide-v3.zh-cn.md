# Pokémon Bank v1.5 Official Bulk Sync V3 编译与发布指南

> 分支：`feature/official-bank-bulk-sync`
>
> 本文面向维护者，说明如何从源码编译 V3、执行 host/ARM/IPS 静态验证、生成 Luma `code.ips`、打包、计算 SHA-256，以及创建 GitHub prerelease。
>
> 不要把 Nintendo/Pokémon Bank 原始 `.code`、CIA、RomFS 或其它版权资源提交进公开仓库或 GitHub Release。

---

## 1. 当前构建架构

V3 编译链分成两部分：

```text
C source
→ ARMv6K Thumb relocatable object
→ armips .importobj
→ stock Pokémon Bank v1.5 .code
→ patched .code
→ Floating IPS
→ code.ips
```

核心文件：

```text
bank/src/official_bulk_sync.h
bank/src/official_bulk_sync_core.c
bank/src/official_bulk_sync.c
bank/src/official_bulk_sync_prod.c
bank/src/official_bulk_sync_host_test.c
bank/src/main_official.s
bank/src/verify_official_bulk_sync.py
bank/src/Makefile
```

输出：

```text
bank/build/official_bulk_sync_prod.o
bank/build/00040000000C9B00.dec.code
bank/build/official-armips-symbols.txt
release/00040000000C9B00/code.ips
```

---

## 2. Stock binary 基线

完整构建必须由维护者自己准备 Pokémon Bank v1.5 解压后的 `.code`：

```text
bank/rom/exefs/00040000000C9B00.dec.code
```

要求：

```text
size: 0x2AC000
SHA-256:
2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

Linux：

```bash
sha256sum bank/rom/exefs/00040000000C9B00.dec.code
```

PowerShell：

```powershell
Get-FileHash .\bank\rom\exefs\00040000000C9B00.dec.code -Algorithm SHA256
```

如果 hash 不一致，停止构建。当前所有地址、code cave 和 verifier 都只针对这个基线。

---

## 3. 工具要求

最少需要：

```text
GNU make
Python 3
ARM GCC / devkitARM
armips
Floating IPS CLI (flips)
本机 C compiler（host test）
```

推荐：

```text
arm-none-eabi-gcc
arm-none-eabi-nm
arm-none-eabi-readelf
arm-none-eabi-size
```

### 3.1 `DEVKITARM`

Makefile 要求环境变量：

```bash
export DEVKITARM=/opt/devkitpro/devkitARM
```

Windows/MSYS2 示例：

```bash
export DEVKITARM=/c/devkitPro/devkitARM
```

Makefile 实际调用：

```text
$DEVKITARM/bin/arm-none-eabi-gcc
```

### 3.2 armips

仓库默认路径：

```text
bank/tools/armips/armips
```

也可以覆盖：

```bash
make -C bank/src ARMIPS=/path/to/armips ...
```

V3 依赖：

```text
.importobj
-erroronwarning
-stat
-sym
```

建议使用已验证支持 `-stat` 的 armips 构建。

### 3.3 Floating IPS

仓库默认路径：

```text
bank/tools/flips/flips
```

可覆盖：

```bash
make -C bank/src IPS_TOOL=/path/to/flips ...
```

---

## 4. 为什么 GitHub CI 不能完成完整 IPS 构建

公开 CI 可以编译：

```text
official_bulk_sync_prod.o
```

并检查 relocation / size / host contract。

但完整 `code.ips` 构建需要 stock：

```text
00040000000C9B00.dec.code
```

该文件不应进入公开 GitHub 仓库/Artifact。

因此当前分工是：

```text
GitHub Actions
→ source-level ARM object validation

维护者本地
→ stock .code + armips + flips
→ full IPS assembly/replay verification
```

不要把“CI object 编译成功”当成“最终 IPS 已完整验证”。

---

## 5. Host contract test

先跑不依赖 3DS runtime 的核心逻辑测试。

因为 Makefile 在 parse 阶段要求 `DEVKITARM`，即使只跑 host test 也要先设置该变量。

Linux：

```bash
export DEVKITARM=/opt/devkitpro/devkitARM
make -C bank/src clean
make -C bank/src host-test CC_FOR_BUILD=cc
```

它覆盖：

```text
0xACA48 / 0xBB518 supported size
header validation
slot empty detection
unchanged slot metadata preserve
occupied→empty historical metadata preserve
empty→occupied metadata generation
occupied→occupied changed metadata refresh
Box metadata copy
state gate
backup path builder
format tag mapping
```

如果 host test 失败，不要继续发布。

---

## 6. 编译 production ARM object

直接执行：

```bash
make -C bank/src ../build/official_bulk_sync_prod.o
```

Makefile 使用的关键选项：

```text
-Os
-march=armv6k
-mtune=mpcore
-mthumb
-mfloat-abi=soft
-ffreestanding
-fno-builtin
-fno-stack-protector
-fno-unwind-tables
-fno-asynchronous-unwind-tables
-fomit-frame-pointer
-fno-common
-ffunction-sections
-fdata-sections
-Wall -Wextra -Werror
```

这是一个 freestanding Thumb payload，不应该偷偷依赖普通 ARM runtime helper。

---

## 7. ARM object 必做检查

### 7.1 大小

```bash
arm-none-eabi-size bank/build/official_bulk_sync_prod.o
```

当前 CI hard limit：

```text
Thumb object text <= 1680 bytes
```

最终 armips payload 还要容纳 ARM dispatcher / literal pool，因此不能把 object budget 吃满。

### 7.2 禁止除法 runtime helper

```bash
arm-none-eabi-nm -u bank/build/official_bulk_sync_prod.o
```

不得出现：

```text
__aeabi_uidiv
__aeabi_idiv
__aeabi_uidivmod
__aeabi_idivmod
```

### 7.3 禁止旧 V2 cross-ISA helper

不得出现 undefined symbol：

```text
OfficialBulk_CommandBuffer
```

并执行：

```bash
arm-none-eabi-readelf -r bank/build/official_bulk_sync_prod.o
```

不得出现：

```text
OfficialBulk_CommandBuffer
```

相关 `R_ARM_THM_CALL` relocation。

原因见：

```text
official-bank-bulk-sync-technical-v3.zh-cn.md
```

V2 实机已经证明该路径会因为 armips external Thumb→ARM relocation 偏差导致 `undefined instruction`。

---

## 8. 完整构建

stock `.code`、工具和环境均准备好后：

```bash
export DEVKITARM=/opt/devkitpro/devkitARM
make -C bank/src clean
make -C bank/src all
```

`all` 会执行：

```text
1. 编译 official_bulk_sync_prod.o
2. armips main_official.s
3. 生成 patched .code
4. flips 生成 code.ips
5. verify_official_bulk_sync.py
```

成功输出：

```text
release/00040000000C9B00/code.ips
```

---

## 9. armips 布局约束

V3 只允许修改：

```text
0x002AF460 .. 0x002AF464
    BankDataSyncState_Update hook

0x00313910 .. 0x00314000
    RX text-tail payload
```

关键入口：

```text
0x00313910  OfficialBulk_BankDataSyncDispatch
```

`OfficialBulkSync_Process` 的准确地址由本次构建 symbol file + verifier 固定检查。

当前架构禁止重新使用：

```text
0x0036A000 .. 0x003AC000
```

作为 code/scratch cave。

该区是 mapped data/global image。

---

## 10. 静态 verifier

`make all` 最后会运行：

```text
bank/src/verify_official_bulk_sync.py
```

也可手动执行：

```bash
python3 bank/src/verify_official_bulk_sync.py \
  --base bank/rom/exefs/00040000000C9B00.dec.code \
  --patched bank/build/00040000000C9B00.dec.code \
  --symbols bank/build/official-armips-symbols.txt \
  --ips release/00040000000C9B00/code.ips
```

它至少验证：

```text
stock SHA-256 完全匹配
patched .code 长度不变
原 RX text cave 原本为 0
任何 changed byte 都只能落在 allowlist
BankDataSync hook 确实发生变化
mapped .data 0x0036A000..0x003AC000 逐字节不变
关键 symbols 地址正确
禁止旧 OfficialBulk_CommandBuffer symbol
IPS replay 后必须与 patched .code 完全一致
```

只有 verifier PASS 的 IPS 才进入发布候选。

---

## 11. GitHub CI

当前 feature 分支 CI：

```text
.github/workflows/official-bulk-sync-ci.yml
```

触发：

```text
push to feature/official-bank-bulk-sync
或 workflow_dispatch
```

当前 CI 执行：

```text
host merge/state-gating contract test
ARMv6K Thumb -Werror build
arm-none-eabi-size / objdump
__aeabi runtime helper rejection
OfficialBulk_CommandBuffer symbol rejection
OfficialBulk_CommandBuffer relocation rejection
payload text budget <= 1680
上传 official_bulk_sync_prod.o artifact
```

发布前建议确认最新“源码相关 commit”的这个 workflow 为 success。

注意：只改 Markdown 文档通常不会触发该 workflow，这是正常的，因为 docs 不改变 payload。

---

## 12. 生成发布目录

V3 不需要 RomFS。

发布目录应尽量简单：

```text
00040000000C9B00/
└── code.ips
```

不要把以下内容打包进 release：

```text
stock .code
patched full .code
CIA
RomFS dump
ExHeader
ticket/title key
用户 bankdata
bulk_import.bin
```

---

## 13. 打 ZIP

Linux 示例：

```bash
cd release
zip -r ../PokemonBank_OfficialBulkSync_V3_preview.zip 00040000000C9B00
cd ..
```

PowerShell 示例：

```powershell
Compress-Archive `
  -Path .\release\00040000000C9B00 `
  -DestinationPath .\PokemonBank_OfficialBulkSync_V3_preview.zip `
  -Force
```

检查 ZIP 内应该只有：

```text
00040000000C9B00/code.ips
```

以及你主动加入的 README（如果需要）。

---

## 14. SHA-256

Linux：

```bash
sha256sum \
  release/00040000000C9B00/code.ips \
  PokemonBank_OfficialBulkSync_V3_preview.zip
```

PowerShell：

```powershell
Get-FileHash .\release\00040000000C9B00\code.ips -Algorithm SHA256
Get-FileHash .\PokemonBank_OfficialBulkSync_V3_preview.zip -Algorithm SHA256
```

建议生成：

```text
SHA256SUMS.txt
```

并在 Release body 中也写一次关键 hash。

当前已发布 V3 Preview 的已知值：

```text
code.ips
9D17E1126316878497E07D1D1234860227B031EB26A9B9100C82B24806E3BDEE

PokemonBank_OfficialBulkSync_V3_interwork_fix_20260919.zip
C0B3406A2E1EB8294C48B4A0816EE2CBADCEB4C605667E0C30D8A687D86A0E8E
```

新构建如果源码或编译器发生变化，hash 当然可以变化；不要为了匹配旧 hash 而跳过重新验证。

---

## 15. Release target 的选择

建议 Release tag 固定到一个**已经包含：源码 + 技术文档 + 使用文档/必要说明**的明确 commit，而不是指向临时发布 payload commit。

推荐先记录：

```bash
git rev-parse HEAD
```

然后创建 tag/release 时明确：

```text
--target <verified-commit-sha>
```

这样即使之后继续清理一次性 release workflow，Release 的 source snapshot 仍然稳定。

---

## 16. GitHub Release：CLI 方法

准备：

```text
code.ips
PokemonBank_OfficialBulkSync_V3_preview.zip
SHA256SUMS.txt
release-notes.md
```

建议先发 prerelease：

```bash
gh release create official-bulk-sync-v3-preview-YYYYMMDD \
  --repo 969981/bank_and_mover_offline_patch \
  --target <verified-commit-sha> \
  --title "Pokémon Bank Official Bulk Sync V3 Preview" \
  --notes-file release-notes.md \
  --prerelease \
  release/00040000000C9B00/code.ips \
  PokemonBank_OfficialBulkSync_V3_preview.zip \
  SHA256SUMS.txt
```

发布后检查：

```bash
gh release view official-bulk-sync-v3-preview-YYYYMMDD \
  --repo 969981/bank_and_mover_offline_patch
```

并确认每个 asset 都存在。

---

## 17. GitHub Release：网页方法

如果不用 `gh`：

```text
GitHub repository
→ Releases
→ Draft a new release
→ New tag
→ Target 选择已验证 commit
→ Title
→ Release notes
→ 勾选 Set as a pre-release
→ 上传 code.ips / ZIP / SHA256SUMS.txt
→ Publish release
```

发布后重新打开 Release 页面，检查：

```text
tag
Target commit
Prerelease 状态
asset 名称
asset 大小
下载是否正常
```

---

## 18. Release notes 必须写什么

至少写清：

### 架构

```text
单 Hook：BankDataSyncState_Update @ 0x002AF460
payload：RX text tail 0x00313910..0x00314000
不再使用 mapped .data/BSS
```

### 输入

```text
/3ds/Bank/bulk_import.bin
0xACA48 或 0xBB518
只读/data-only
```

### 原版路径保持

```text
login/game selection
Save UI
PrepareUpdate
HPP upload
CompleteUpdate
Rollback
HOME
```

### 验证状态

必须区分：

```text
已静态/CI验证
已实机验证
尚未验证
```

在官方 Save → redownload round-trip 尚未闭环前，必须继续标记为：

```text
Experimental / Prerelease
```

### 安装

明确：

```text
只需要 code.ips
V3 不需要旧 romfs
```

### SHA-256

把 release asset 的 hash 写入 notes 或 `SHA256SUMS.txt`。

---

## 19. 当前 V3 Release 作为参考

Tag：

```text
official-bulk-sync-v3-preview-20260919
```

Release name：

```text
Pokémon Bank Official Bulk Sync V3 Preview
```

该 Release 使用 prerelease 状态，并包含：

```text
code.ips
PokemonBank_OfficialBulkSync_V3_interwork_fix_20260919.zip
SHA256SUMS.txt
```

它固定到当时包含 V3 原理/技术文档的 release target commit，而不是后续清理一次性 workflow 的 commit。

---

## 20. 发布后回归检查

不要以“GitHub Release 创建成功”作为最终验证。

至少再检查：

```text
[ ] Release tag 指向预期 commit
[ ] code.ips asset size 正确
[ ] code.ips SHA-256 与本地一致
[ ] ZIP SHA-256 与本地一致
[ ] SHA256SUMS.txt 内容正确
[ ] Release 标记为 prerelease
[ ] Release notes 没有宣称未完成的 server round-trip 已验证
[ ] 仓库没有误提交 stock .code/CIA/RomFS
[ ] 仓库没有残留临时 base64 binary payload
```

---

## 21. 修改源码后的完整发布清单

推荐严格按以下顺序：

```text
1. 修改源码
2. host test
3. ARM Thumb -Werror
4. nm/readelf relocation guard
5. size budget
6. GitHub CI success
7. 本地准备正确 stock .code
8. make clean
9. make all
10. verifier PASS
11. 实机 H0
12. 实机 H1-preview（如果改到 runtime 路径）
13. 生成 ZIP
14. 生成 SHA256SUMS.txt
15. 更新技术/使用文档
16. 固定 verified release target commit
17. GitHub prerelease
18. 重新核对 release assets/digests
```

如果修改涉及：

```text
state gate
BankObject pointer chain
FS IPC
ARM/Thumb interworking
metadata writer
save/upload hook
```

则必须重新做对应实机验证，不能因为旧版本测试过就跳过。

---

## 22. 关于正式版

在以下证据闭环之前，不建议把 V3 标为 stable/full release：

```text
H0 正常联动
H1-preview 正常 backup/apply
1 Pokémon Save → bulk off → server redownload
30 Pokémon
300 Pokémon
大规模 100 Box
HOME downstream 验证
```

尤其必须通过：

```text
保存后移走 bulk_import.bin
→ 重新联网下载
→ server 内容仍正确
```

否则不能证明官方持久化真正完成。

---

## 23. 相关文档

- `official-bank-bulk-sync-usage-v3.zh-cn.md`：最终用户使用与分级实机验证；
- `official-bank-bulk-sync-principles-v3.zh-cn.md`：完整端到端原理；
- `official-bank-bulk-sync-technical-v3.zh-cn.md`：V2 ARM/Thumb crash 与 V3 修复；
- `official-bank-bulk-sync-design.zh-cn.md`：设计契约；
- `saveboxes-transaction-analysis.zh-cn.md`：原版保存事务；
- `.github/workflows/official-bulk-sync-ci.yml`：公开源码 CI guard；
- `bank/src/verify_official_bulk_sync.py`：完整 IPS 静态边界验证。
