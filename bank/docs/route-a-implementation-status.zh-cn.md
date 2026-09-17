# Pokémon Bank Route A 当前实现状态

本文记录 `research/saveboxes-transaction-analysis` 分支在 Route A 的实际完成度与验证证据。它用于区分“代码已实现/host 已验证”和“仍需 3DS/官方服务实测”的部分。

## 1. 当前目标

```text
完整 bankdata.bin (0xBB518)
    -> 导出 PKHeX 兼容视图 (0xACA48)
    -> PKHeX 编辑主 100 Box
    -> 安全回灌到完整 current image
    -> bulk_import.bin
    -> 3DS Offline Mode
    -> 只覆盖 runtime 主 100 Box
    -> 原版 Bank UI
    -> 正常离线保存
    -> restart + reload
```

D6 Official Mode 仍保持关闭；在 Offline 闭环实机验证完成前，不进入服务器写入测试。

## 2. 已完成：R4/R5/R6 baseline 与策略

真实 `0xBB518` baseline 的 current-only 区域观测：

- `8×0x44` source summaries：每个 entry 只有相同相对偏移 `+0x1A = 0x02` 非零；
- `0x7260` block：以 `NKZT` 开头，baseline 极稀疏，因此现阶段统一称 opaque/NKZT block；
- counters：raw `3C 00 00 00`，`<HH>` 视图为 `[60, 0]`；
- tail：只有首字节 `1` 非零。

V0 策略全部为：

```text
PRESERVE_RUNTIME
```

即 source summaries、NKZT、counters、tail 不从 `bulk_import.bin` 覆盖。

静态仓库搜索没有找到这些 runtime object 大偏移的直接文本引用；因此当前结论来自文件布局、真实 baseline 和 legacy migration 行为，不能宣称这些块的完整业务语义已经逆清。后续仍需原二进制/IDA xref 与 controlled before/after 实验。

## 3. 已完成：D1 BankV15Image

`ViewerForBankdata/tools/bank_v15_image.py`：

- 严格接受 `0xBB518`；
- version 必须为 `2`；
- boxCount 必须为 `100`；
- parse/serialize byte-identical；
- 未知区域 opaque preserve；
- `apply_main_boxes_from()` 实现 Route A V0 白名单模型。

V0 唯一 COPY_FROM_BULK 区域：

```text
0x00017C .. 0x0AAF14 (end-exclusive)
```

## 4. 已完成：D2 bankbulk / PKHeX workflow

支持：

```text
validate
inspect
export-pkhex
import-pkhex
build
apply-v0
```

PKHeX 导出：

```powershell
python .\tools\bankbulk.py export-pkhex `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bankdata_pkhex_view.bin"
```

兼容视图固定 `0xACA48 / 707144 bytes`。

PKHeX 编辑后安全回灌：

```powershell
python .\tools\bankbulk.py import-pkhex `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bankdata_pkhex_view_edited.bin" `
  -o "D:\Bank\bulk_import.bin"
```

只回灌主 100 Box，不回灌 Header、Transfer Box、`0xACA44..0xACA47` overlap 或 current-only metadata。

`apply-v0` 可以在 PC 上生成理论 runtime 结果，供 3DS 保存后比对：

```powershell
python .\tools\bankbulk.py apply-v0 `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bulk_import.bin" `
  -o "D:\Bank\expected_after_apply.bin"
```

## 5. 已完成：D3/D4 Offline Apply V0 实现

新增：

```text
bank/src/bulk_import.h
bank/src/bulk_import.c
bank/src/bulk_import_host_test.c
```

构建时原 proven loader 通过预处理重命名为：

```text
OfflinePatch_LoadBankData_Base
```

新的 `OfflinePatch_LoadBankData` wrapper：

1. 调用原 proven loader 读取 `/3ds/Bank/bankdata.bin`；
2. 定位 runtime `BankObject+8` body；
3. 检查 `/3ds/Bank/bulk_import.bin`；
4. 检查文件大小严格为 `0xBB518`；
5. 只读 `0x15C..0x15F` 验证 version=2 / boxCount=100；
6. 直接把 `0x17C..0xAAF14` 从 bulk 文件读入 runtime 同一区域；
7. Header、Transfer Box、tag/source/time、R4/R5/R6 区域保持 runtime 值；
8. 若大块读取发生 short/error，重新调用原 proven loader 恢复完整 `bankdata.bin`，避免半应用对象进入 Bank UI。

### 当前 V0 的行为

- `bulk_import.bin` 缺失：正常 Offline Mode，不修改 runtime；
- bulk 尺寸/头无效：不应用 bulk，继续使用原 bankdata；
- bulk 有效：自动应用主 100 Box；
- 不自动保存；
- 不自动删除/重命名 bulk 文件；
- 用户不保存退出时，原 `bankdata.bin` 不会被新内容替换；
- bulk 文件仍在时，下次启动会再次应用。

第一版暂时没有 A/B 确认 UI，目标是先验证最小数据路径和保存闭环。

## 6. 自动验证结果

### Python

当前 Route A / D0-D5 相关测试：

```text
31 tests
0 failures
```

覆盖：

- Bank v1.5 物理布局；
- legacy/current 4-byte overlap；
- structured diff；
- BankV15Image byte-identical round-trip；
- PKHeX export/import；
- V0 whitelist；
- R4/R5/R6 raw classifier；
- 1 slot；
- 1 Box；
- 10 Boxes；
- 100 Boxes。

### Host C

`bulk_import_host_test.c` 用普通 host C 编译运行通过，确认：

```text
0x000000                  preserve runtime
0x00017B                  preserve runtime
0x00017C                  copy bulk
0x00017C..0x0AAF13        copy bulk
0x000AAF14                preserve runtime
0x000ACA44                preserve runtime
0x000BB517                preserve runtime
```

### ARM target compile

`bulk_import.c` 使用与项目一致的 freestanding ARMv6K 警告等级，通过 clang ARM target 编译：

```text
-Wall -Wextra -Werror
```

wrapper object text 约 `0x21B` bytes。

### 真实 bankdata baseline

上传的真实 `bankdata.bin` 已做：

```text
current full
 -> export-pkhex
 -> unchanged import-pkhex
 -> full current
```

结果 byte-identical。

再做：

```text
runtime == bulk
 -> apply-v0
```

结果同样 byte-identical。

真实用户 Bank 数据本身未提交到仓库。

## 7. 当前环境无法完成的验证

当前执行环境没有 devkitARM，也没有仓库的原版 `00040000000C9B00.dec.code` 构建输入，因此没有在本会话生成最终 `code.ips`。

这意味着以下内容仍必须在本地完整工具链/3DS 上验证：

- arm-none-eabi-gcc + armips 最终链接后的 payload 是否仍位于 audited code cave；
- `verify_patch.py` 全量通过；
- 真实 Bank UI 是否能正确显示导入后的 Pokémon；
- 原版离线 save state 是否能序列化并安装新 `bankdata.bin`；
- restart + reload 是否保持预期主 Box；
- tag/source/timestamp 陈旧值是否影响 UI、移动、保存或后续 HOME 语义。

## 8. D5 实机验证清单

建议先使用当前 baseline 的干净测试槽（例如之前识别出的全零槽）逐级验证：

```text
T0 no-op bulk
T1 1 occupied -> empty
T2 1 empty -> occupied
T3 overwrite 1 slot
T4 1 Box
T5 10 Boxes
T6 100 Boxes
```

每次流程：

```text
备份 bankdata.bin / bankdata.bak
    -> 生成 bulk_import.bin
    -> 生成 expected_after_apply.bin
    -> 放到 sd:/3ds/Bank/bulk_import.bin
    -> Offline Mode 进入 Bank Box UI
    -> 检查
    -> 正常保存
    -> 暂时移走 bulk_import.bin
    -> restart
    -> 重新进入 Offline Mode
    -> 导出/取得 saved bankdata.bin
    -> diff saved vs expected
```

特别注意：重启验证前必须先把 `bulk_import.bin` 移走，否则下一次启动会再次应用 bulk，无法证明保存后的 `bankdata.bin` 本身已经正确持久化。

## 9. D6 状态

**尚未启用。**

D6 只在上述 Offline 实机闭环通过后实施。第一轮只允许 1 Pokémon，并采用：

```text
server_before.bin
 -> fresh official download
 -> Route A whitelist apply
 -> manual inspect
 -> stock official save
 -> fresh redownload
 -> server_after.bin
 -> structured diff
```

不重写 NEX/HPP 上传协议，不把 PC bulk 的账户/header/transaction 字段带入 official runtime。
