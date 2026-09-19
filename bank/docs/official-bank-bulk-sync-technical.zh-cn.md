# Pokémon Bank v1.5 Official Bulk Sync 详细技术文档

> 分支：`feature/official-bank-bulk-sync`
>
> 目标：保持 Pokémon Bank 原版联网、菜单、保存和 HOME 流程，仅在普通游戏联动的官方 Bank 下载完成后，对 fresh runtime `BankObject` 做一次“先备份、后只读导入”的主 100 Box 合并。
>
> 当前状态：代码、host contract test、ARM freestanding 编译、armips 静态构建、IPS replay/verifier 已通过；**官方服务器 Save → redownload round-trip 尚需实机分级验证**。

---

## 1. 最终用户流程

本分支不再使用用户可见的 Offline Mode / Download Mode。用户看到和操作的都是原版 Bank 流程：

```text
启动 Pokémon Bank
        ↓
原版联网 / 登录
        ↓
原版选择任意兼容游戏
        ↓
普通 Bank state 16
        ↓
官方下载 fresh BankObject
        ↓
[补丁：pending marker]
        ↓
下一次 BankDataSyncState_Update
        ↓
[补丁：备份 fresh BankObject]
        ↓
[补丁：只读读取 bulk_import.bin]
        ↓
[补丁：slot-aware Pokémon + metadata merge]
        ↓
继续原版 Bank UI
        ↓
用户人工检查
        ↓
用户执行原版“保存并退出”
        ↓
原版 Serialize / PrepareUpdate / HTTP/HPP / CompleteUpdate
        ↓
官方服务器持久化
        ↓
之后正常走 Bank → HOME
```

如果 `SD:/3ds/Bank/bulk_import.bin` 不存在、大小不支持或 header 不合法，则补丁不做 bulk merge，仍继续原版 Bank 流程。

---

## 2. 强制设计契约

### 2.1 `bulk_import.bin` 永远只读

补丁只用 `OPEN_READ` 打开 `bulk_import.bin`。

无论：

- bulk Apply 成功；
- 用户保存成功；
- 用户保存失败；
- 原版 rollback；
- 用户退出；
- Bank 重启；

补丁都**不会**：

- 删除 `bulk_import.bin`；
- 重命名 `bulk_import.bin`；
- 覆盖 `bulk_import.bin`；
- 回写 tag/source/timestamp；
- 生成 `bulk_import_uploaded_*` 副本。

因此用户可以长期保留同一份 `bulk_import.bin`。只要它仍存在，每次普通 game-linked Bank 下载后都会再次比较并 Apply。

### 2.2 bulk 只提供主 100 Box 数据

支持：

```text
0xACA48  PKHeX Bank7 兼容视图
0xBB518  Pokémon Bank v1.5 current image
```

无论哪种格式，联网路线只读取主 100 Box：

```text
0x00017C .. 0x0AAF14
```

每个 Box：

```text
30 × 0xE8 Pokémon record
+ 0x26 Box metadata
= 0x1B56 stride
```

bulk 中下列区域**绝不作为权威来源**：

```text
Header / identity
Transfer Box
BankTags[3000]
TransferTags[30]
source summary
NKZT block
counters
SourceSoftware[3000]
Timestamp[3000]
tail / reserved
remote/session/account state
```

### 2.3 原版上传事务完全保留

本分支不生成、不持久化、不复用：

```text
dataId
curVersion
updateVersion
transactionPassword
applicationId
signed URL
HTTP headers/form fields
login/auth/session
```

用户点击保存后继续执行原版：

```text
BankSaveState_Update
→ BankSave_SerializeAndStage
→ BankRemote_StageFileUpdate
→ PrepareUpdateBankObject
→ stock HTTP/HPP upload
→ CompleteUpdateBankObject
→ Commit / Rollback
```

本分支当前没有 Hook `BankSaveState_Update`、`BankSave_SerializeAndStage`、Prepare/CompleteUpdate 或 HOME state 28。

---

## 3. Bank v1.5 相关布局

当前代码使用的核心常量：

```c
BANK_V15_SIZE            0xBB518
BANK_G7_PKHEX_VIEW_SIZE  0xACA48

BANK_V15_VERSION_OFFSET  0x15C
BANK_V15_BOX_COUNT_OFFSET 0x15E

BANK_V15_MAIN_BOX_START  0x17C
BANK_V15_MAIN_BOX_END    0xAAF14

BANK_V15_BOX_COUNT       100
BANK_V15_SLOTS_PER_BOX   30
BANK_V15_PKM_SIZE        0xE8
BANK_V15_BOX_META_SIZE   0x26
BANK_V15_BOX_STRIDE      0x1B56

BANK_V15_TAG_START       0xACA44
BANK_V15_SOURCE_START    0xB4AA0
BANK_V15_TIMESTAMP_START 0xB5658
```

slot index：

```text
index = box * 30 + slot
```

slot Pokémon address：

```text
0x17C
+ box * 0x1B56
+ slot * 0xE8
```

parallel metadata：

```text
tag       = 0xACA44 + index
source    = 0xB4AA0 + index
timestamp = 0xB5658 + index * 8
```

`BankObject` runtime object 本身带 8-byte object header；序列化文件 body 对应 `object + 8`。

当前 object vtable 仍要求：

```text
*(u32 *)object == 0x003626FC
```

---

## 4. Official-only Hook 架构

### 4.1 只使用两个 Hook

当前 `main_official.s` 只改两个原版执行点：

```text
BankRemote_DownloadSuccessCallback + 0x14
= 0x002D11C4

BankDataSyncState_Update
= 0x002AF460
```

设计目的：

1. async download callback 只负责“普通 Bank 下载完成”的轻量 marker；
2. 不在 async callback 里做 SD I/O；
3. 真正 backup / bulk read / merge 放到下一帧 `BankDataSyncState_Update`；
4. merge 后立即继续原版 `BankDataSyncState_Update + 4`。

### 4.2 Download marker trampoline

`OfficialBulk_DownloadMarkerTrampoline` 位于：

```text
0x00313910
```

原版 callback `+0x14` 被覆盖的指令是：

```text
ldr r8, =0x000BB528
```

trampoline 行为：

```text
保存 r0-r3/r12/lr + CPSR flags
        ↓
读取 [r4 + 0x41]
        ↓
== 0 ?
  YES → 写 OfficialBulk_Scratch = 1
  NO  → 不标记
        ↓
恢复 flags/registers
        ↓
重放 ldr r8, =0x000BB528
        ↓
返回原 callback
```

当前逆向结论中 `[r4+0x41] == 0` 对应普通 game-linked Bank 下载；非零路径不会设置 bulk pending marker，因此 HOME / 非普通路径不会进入 Apply。

### 4.3 Pending marker

pending byte：

```text
OfficialBulk_Scratch = 0x003ABFFC
```

这个地址在文件镜像中保持原始 zero，不写入 IPS；运行时只作为 1-byte pending flag。

流程：

```text
download success
→ scratch = 1
→ 下一次 BankDataSyncState_Update
→ 读取 scratch
→ 清 0
→ OfficialBulkSync_Process(state)
→ 继续 native BankDataSyncState_Update + 4
```

marker 在调用 `OfficialBulkSync_Process` 之前先清零，因此一次普通下载只消费一次，不会每帧重复 Apply。

---

## 5. Runtime BankObject 获取

`OfficialBulkSync_Process(state)` 使用现有 state/flow 关系：

```c
flow   = *(u8 **)(state + 8);
object = flow ? *(u8 **)(flow + 0xCC) : 0;
body   = object + 8;
```

进入处理前验证：

```text
object != NULL
*(u32 *)object == 0x003626FC
u16(body + 0x15C) == 2
u16(body + 0x15E) == 100
```

如果 object 或 header 不满足条件，本次 processing 直接失败并返回 native flow，不继续 merge。

---

## 6. Fresh server Bank 备份

### 6.1 顺序

备份发生在任何 bulk 修改之前：

```text
fresh server BankObject
        ↓
writeSnapshot(...)
        ↓
只有 backup 完整成功
        ↓
才继续 bulk Apply
```

因此 backup 保存的是服务器刚下载的 fresh `0xBB518` body，而不是 Apply 后 candidate。

### 6.2 文件名

目标格式：

```text
/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

日期主体来源于 Bank body header 的日期字段：

```text
0x160 year (u16 LE)
0x162 month
0x163 day
0x164 hour
0x165 minute
0x166 second
```

当前 runtime 若已成功取得 stock timestamp，会用 `timestamp % 60` 替换文件名中的秒字段，使备份秒值与本次 runtime 时间保持一致。

### 6.3 原子性边界

`writeSnapshot`：

```text
OPEN_READ | OPEN_WRITE | OPEN_CREATE
→ set size = 0xBB518
→ FILE_WRITE offset 0, length 0xBB518, WRITE_FLUSH
→ FILE_CLOSE
```

只有：

```text
Result == 0
closeResult == 0
written == 0xBB518
```

才认为 backup 成功。

当前实现假设：

```text
SD:/3ds/Bank/
```

目录已经存在。该目录在前面 Route A 测试流程中已使用；official-only runtime 当前没有额外的 mkdir 逻辑。

---

## 7. Stock-like metadata 获取

`bulk_import.bin` 不提供 tag/source/timestamp；这些值在 runtime 中现场获取。

### 7.1 当前游戏 profile

入口：

```text
GAME_REGISTRY_SLOT = 0x003AB90C
GameModelActive    = 0x00233A6C
```

过程：

```text
registry = *0x003AB90C
model = GameModelActive(*(registry + 0x1C))
profile = model[8]
```

### 7.2 format tag

当前实现映射：

```text
profile 1..4 → tag = 0
profile 5..8 → tag = 1
其它       → unsupported (0xFF)
```

对应当前逆向假设：

```text
Gen6-linked profiles → format tag 0
Gen7-linked profiles → format tag 1
```

该映射已写入 host contract test；正式大规模官方上传前仍应使用 1 Pokémon round-trip 做服务器侧验证。

### 7.3 source software ID

根据当前 active game model 取得 source object：

```text
profile >= 5:
    sourceObject = model + 0x74304

profile < 5:
    sourceObject = model + 0x129AC
```

读取其 vtable：

```text
vtable = *(u32 **)sourceObject
getter = vtable[3]   // +0x0C
sourceSoftware = getter(sourceObject)
```

这样 source software 不从 bulk 的 Pokémon Origin Game 推断，而直接复用当前联动游戏在 stock runtime 中暴露的软件 ID。

这与前期真实样本研究一致：source software 描述最后一次 Bank 写入时的联动软件，而不是 Pokémon 原始捕获游戏。

### 7.4 timestamp

当前实现复用原版时间链：

```text
TIME_CONTAINER_INIT = 0x00234648
TIME_QUERY          = 0x001D3BF4
TIME_PACK           = 0x001F2BD4
```

流程：

```text
TIME_CONTAINER_INIT(stamp)
→ TIME_QUERY(*(root + 0x138), stamp)
→ TIME_PACK(stamp)
→ u64 Bank timestamp
```

这避免自行重新实现 Bank 时间编码。

前期样本分析已经表明该值与 Nintendo 2000 epoch 秒高度一致；official-only 实现仍优先调用 stock helper，而不是自己算 epoch。

---

## 8. Slot-aware merge 算法

核心函数：

```c
OfficialBulk_MergeSlot(
    runtimeBody,
    box,
    slot,
    bulkRecord,
    meta
)
```

### 8.1 unchanged

如果 runtime 的 `0xE8` record 与 bulk 完全一致：

```text
Pokémon    不写
Tag        保持 fresh server
Source     保持 fresh server
Timestamp  保持 fresh server
```

避免只因为 bulk 文件一直存在，就每次重新登录都刷新 metadata。

### 8.2 changed → empty

如果 bulk record 为全零：

```text
写入全零 Pokémon record
Tag        保留 server 历史值
Source     保留 server 历史值
Timestamp  保留 server 历史值
```

这是基于真实 `bankdata.bin` 的观察：大量已空槽仍保留 tag/source/timestamp 历史数据。

### 8.3 empty → occupied

如果 payload changed 且新 record 非空：

```text
写入 bulk Pokémon
Tag        = 当前联动 profile 对应 tag
Source     = stock 当前联动 software ID
Timestamp  = stock 当前时间编码
```

### 8.4 occupied → occupied changed

同样视作一次 replace/deposit：

```text
写入新 Pokémon
刷新 Tag
刷新 Source
刷新 Timestamp
```

### 8.5 Box metadata

每个 Box 的：

```text
0x26 bytes
```

来自 bulk 并完整复制，包括 Box name/index 等主 Box metadata。

这部分属于 bulk 的“Box 数据源”，与 current-only slot metadata 分离。

---

## 9. `bulk_import.bin` 文件读取

### 9.1 路径

```text
/3ds/Bank/bulk_import.bin
```

### 9.2 支持长度

```text
0xACA48
0xBB518
```

### 9.3 header 验证

读取：

```text
offset 0x15C, length 4
```

要求：

```text
u16 version  == 2
u16 boxCount == 100
```

### 9.4 流式读取

runtime 实现没有申请完整 `0xACA48/0xBB518` bulk buffer，而是逐 Box/逐 slot 读取：

```text
for box 0..99:
    for slot 0..29:
        read 0xE8
        merge slot
    read 0x26 Box metadata
    copy Box metadata
```

优点：

- payload 内存占用小；
- 不需要额外 700+ KiB heap；
- 可以直接复用 Bank runtime object 作为 destination。

### 9.5 partial-read 恢复

如果开始 merge 后出现：

- short read；
- FS read error；
- Box metadata read error；
- close error；

`applyBulkFile` 返回 `-1`，表示 runtime 可能已经部分修改。

随后：

```text
restoreSnapshot(刚才的 fresh backup)
```

把完整 `0xBB518` fresh server body 读回 runtime。

因此用户不会因为 bulk 文件中途读坏而进入“半个 Box 是 bulk、半个 Box 是 server”的 UI 状态。

---

## 10. HOME 路径排除

本分支没有 Hook state 28，也没有在所有 full-download 路径无条件 Apply。

是否设置 pending marker 由 download callback 中：

```text
[r4 + 0x41] == 0
```

控制。

当前设计意图：

```text
普通 game-linked Bank download → marker = 1
HOME / 其它非普通 full download → marker 不设
```

因此后续：

```text
Bank → HOME
```

重新下载官方 Bank 时不会再次把本地 bulk 注入 HOME transfer runtime。

D6H 实机验证必须把 HOME 路径也列入回归项，确认实际 state 28 不产生 timestamp backup / bulk Apply。

---

## 11. Code cave 与 IPS 改动范围

### 11.1 Hook bytes

```text
0x002AF460 .. 0x002AF464
BankDataSyncState_Update entry hook

0x002D11C4 .. 0x002D11C8
DownloadSuccess callback marker hook
```

### 11.2 Runtime payload cave

```text
0x00313910 .. 0x00314008
```

当前包含：

- `OfficialBulk_DownloadMarkerTrampoline`
- `OfficialBulk_BankDataSyncDispatch`
- `OfficialBulkSync_Process`
- FS/runtime metadata helper code

最近静态构建使用约：

```text
1719 / 1784 bytes
```

剩余约 65 bytes。

### 11.3 Core payload cave

```text
0x003ABA90 .. 0x003ABFFC
```

用于纯 merge/layout/helper 逻辑。

最近静态构建使用约：

```text
1005 / 1388 bytes
```

剩余约 383 bytes。

### 11.4 Scratch

```text
0x003ABFFC
```

只作为 runtime pending byte。

IPS verifier 明确要求：

```text
0x003ABFFC .. 0x003AC000
```

在文件镜像里继续与原版完全一致；scratch 不靠预写 patch 初始化。

---

## 12. Static verifier

`verify_official_bulk_sync.py` 强制检查：

### 12.1 原版基线 SHA-256

```text
2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

对应 Pokémon Bank v1.5：

```text
00040000000C9B00.dec.code
```

### 12.2 允许修改的地址范围

只允许：

```text
0x002AF460..0x002AF464
0x002D11C4..0x002D11C8
0x00313910..0x00314008
0x003ABA90..0x003ABFFC
```

任何其它地址发生 byte diff，verifier 直接失败。

### 12.3 Code cave 原版必须全零

在 patch 前要求两个 payload cave 均为原版 zero region，避免覆盖未知 stock code/data。

### 12.4 Symbol 固定

当前关键 symbol：

```text
OfficialBulk_DownloadMarkerTrampoline = 0x00313910
OfficialBulk_BankDataSyncDispatch     = 0x00313958
OfficialBulkSync_Process              = 0x0031398C
OfficialBulk_CoreStart                = 0x003ABA90
OfficialBulk_Scratch                  = 0x003ABFFC
```

### 12.5 IPS replay

verifier 自己实现 IPS replay：

```text
base .code + code.ips
```

必须逐字节等于 armips 生成的 patched `.code`。

这样避免出现“armips 输出是一份、Release 的 IPS 又是另一份”的情况。

---

## 13. Build 系统

当前默认 `bank/src/Makefile` 已切换到 official-only build。

### 13.1 production objects

```text
official_bulk_sync.c
→ official_bulk_sync.o

official_bulk_sync_core.c
→ official_bulk_sync_core.o
```

编译参数：

```text
-std=c11
-Os
-march=armv6k
-mtune=mpcore
-marm
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

### 13.2 armips

```text
main_official.s
```

把两个 object 分别 import 到两个 verified zero caves。

### 13.3 IPS

使用 flips：

```text
base .code
vs
patched .code
→ code.ips
```

### 13.4 旧 Route A Preview

原 Offline/Download 双模式构建入口保存在：

```text
Makefile.route-a-preview
main.s
bulk_import.c
patch.c
```

但 feature 分支默认 `make` 已经构建 official-only 版本。

---

## 14. Freestanding ARM 约束

一次 fresh ARM build 曾发现 `/10`、`%60` 等表达式会生成：

```text
__aeabi_uidiv
__aeabi_uidivmod
```

这类外部运行库 helper 不适合直接 `.importobj` 到 armips code cave，因为 payload 没有常规 ELF dynamic/runtime linkage。

当前实现已经把相关十进制格式化逻辑改成不依赖 ARM EABI division helper 的 freestanding 实现。

CI 额外检查 ARM object，拒绝未预期的 `__aeabi_*` helper 依赖。

---

## 15. 测试矩阵

### 15.1 Host merge contract test

覆盖：

```text
supported size: 0xACA48 / 0xBB518
unsupported size reject
header version/boxCount validation
unchanged slot preserves metadata
empty→occupied writes tag/source/timestamp
occupied→occupied changed refreshes metadata
occupied→empty preserves historical metadata
Box metadata copy
backup path formatting
Gen6/Gen7 profile→tag mapping
```

### 15.2 ARM compile

GitHub Actions 使用 `gcc-arm-none-eabi`：

```text
-Wall -Wextra -Werror
ARMv6K runtime compile
ARMv6K core compile
unexpected __aeabi helper check
```

### 15.3 Python regression

前期 Route A / Bank v1.5 工具链现有 Python regression 继续执行；当前开发阶段已跑到 43 tests 通过。

### 15.4 Static IPS verification

本地使用拥有合法原版 `00040000000C9B00.dec.code` 的构建环境执行：

```text
base SHA verify
armips build
allowed diff range verify
symbol verify
IPS replay verify
```

---

## 16. 当前测试版 IPS

当前开发阶段最近一次静态构建：

```text
code.ips SHA-256:
688574E391396C18F88C30272FE5A8590481F0766647C056E31ADF7C6E919B20
```

该值属于当前 preview 构建，不应当作为未来 commit 的永久固定值；每次修改 payload 后都要重新构建并记录新的 digest。

---

## 17. 与前一版 Scheme B 的区别

### Scheme B Offline Preview

```text
用户选择 Offline Mode
→ 本地 bankdata.bin
→ bulk apply
→ 本地 save
```

并且带自定义 RomFS 文案。

### Official Bulk Sync

```text
完全原版 UI / 网络流程
→ 官方 fresh Bank download
→ backup
→ bulk merge
→ 原版 Box UI
→ 原版官方 save/upload
```

因此测试 official-only 版本时应移走旧版：

```text
luma/titles/00040000000C9B00/romfs/
```

当前 official-only preview 只需要新的 `code.ips`，不依赖 Route A Preview 的自定义 RomFS。

---

## 18. 当前未完成 / 待验证事项

### 18.1 官方服务器 round-trip

尚未声明完成的关键验证：

```text
Apply 1 Pokémon
→ 原版保存成功
→ 退出
→ 再次官方登录
→ redownload
→ server_after 确认 Pokémon + metadata 被服务器接受
```

必须完成后才能继续扩大规模。

### 18.2 推荐 D6H 阶梯

```text
H0: no-op bulk / unchanged
H1: 1 Pokémon
H2: 30 Pokémon / 1 Box
H3: 300 Pokémon / 10 Boxes
H4: 3000 slots / 100 Boxes
H5: HOME transfer verification
```

每一阶段保存：

```text
fresh server backup
bulk_import.bin
runtime expected
server_after redownload
structured diff report
```

### 18.3 tag 映射服务器验证

`profile 1..4 → 0`、`5..8 → 1` 已由静态逆向 + 本地样本支持，但需要官方 1 Pokémon round-trip 最终确认服务器接受。

### 18.4 source software 映射验证

当前实现直接调用 stock runtime getter，是比硬编码游戏 ID 更稳的方案；仍应通过 server_after 验证实际落盘值与普通 Bank deposit 一致。

### 18.5 counter / summary / NKZT

当前 implementation 不主动改：

```text
source summaries
NKZT
counters
tail
```

这是有意设计。

D6H 单 Pokémon round-trip 后应比较：

```text
fresh backup
vs
server_after
```

确认原版 Save/服务器是否自动派生或更新这些区域。如果服务器要求额外一致性，再继续追 stock setter/derived-field 生成路径，而不是直接复制 bulk 中的未知 metadata。

---

## 19. 故障模型

### bulk 不存在

```text
fresh Bank backup 仍可生成
bulk open fails
→ no apply
→ 原版流程继续
```

### bulk size/header 不合法

```text
不写 runtime Box
→ 原版流程继续
```

### backup 写失败

```text
不允许开始 bulk merge
→ runtime 保持 fresh server Bank
```

### bulk 中途 read 失败

```text
runtime 可能已部分修改
→ restoreSnapshot(fresh backup)
→ 恢复完整 server Bank
```

### metadata query 失败

```text
backup 完成后不执行 changed-slot merge
→ 避免写入来源未知的 tag/source/timestamp
```

### 官方 Save 失败

补丁没有接管 Save transaction；失败处理完全由原版 Bank rollback/retry UI 负责。

`bulk_import.bin` 不会因保存失败而发生任何变化。

---

## 20. 维护原则

后续修改必须继续遵守：

1. 不在 async download callback 里做文件 I/O；
2. 不 Hook state 28 / HOME bulk apply；
3. 不自制 PrepareUpdate / CompleteUpdate；
4. 不持久化 transactionPassword；
5. bulk 永远只读；
6. bulk current-only metadata 永远不作为权威来源；
7. fresh server Bank 在任何 mutation 前先 backup；
8. partial mutation 必须可恢复；
9. changed-slot metadata 优先调用 stock runtime getter/helper；
10. 每次扩大服务器测试规模前，先 redownload + structured diff。

---

## 21. 关键源码索引

```text
bank/src/main_official.s
    两个 official-only Hook、pending marker、code cave 布局

bank/src/official_bulk_sync.c
    3DS runtime FS I/O、BankObject 获取、stock metadata query、backup、streaming bulk Apply

bank/src/official_bulk_sync_core.c
    layout、slot compare/merge、metadata policy、Box metadata、backup path helper

bank/src/official_bulk_sync.h
    Bank v1.5 常量和公共接口

bank/src/official_bulk_sync_host_test.c
    host contract tests

bank/src/verify_official_bulk_sync.py
    base SHA、允许改动范围、zero-cave、symbol、IPS replay verifier

bank/src/Makefile
    official-only 默认构建

bank/src/Makefile.route-a-preview
    旧 Offline/Download Route A Preview 构建保留入口
```

---

## 22. 当前结论

当前阶段已经完成的工程闭环是：

```text
原版普通 Bank download callback
→ pending marker
→ BankDataSync 下一帧
→ fresh Bank backup
→ 只读 PKHeX/full bulk
→ slot-aware merge
→ stock-derived tag/source/timestamp
→ 原版 Bank UI
```

并且 static verifier 保证官方保存、网络、HOME 等其它代码区域没有被这个 preview 修改。

下一项真正决定联网路线是否成立的证据，不是再增加更多静态代码，而是：

```text
1 Pokémon official save
→ 完整退出
→ 官方 redownload
→ binary diff
```

只有这一步通过后，才进入 30 / 300 / 3000 的扩容验证。
