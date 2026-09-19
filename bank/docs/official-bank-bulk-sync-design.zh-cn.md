# Official Bank Bulk Sync 设计与实现（feature/official-bank-bulk-sync）

## 目标

最终版本不再提供用户可见的 Offline / Download Mode，而是完全沿用 Pokémon Bank 原版联网流程：

1. 正常启动、登录官方服务；
2. 正常选择任意兼容游戏；
3. 普通 Bank 路径 state 16 下载 fresh BankObject；
4. 在任何 bulk 修改前备份完整 fresh BankObject；
5. 若存在 `SD:/3ds/Bank/bulk_import.bin`，将其中主 100 Box 合并进 runtime BankObject；
6. changed occupied slot 的 tag/source/timestamp 使用当前联动游戏与原版时间链生成；
7. 用户进入原版 Bank Box UI 自行检查；
8. 用户执行原版“保存并退出”；
9. 原版 `PrepareUpdate / HPP upload / CompleteUpdate / rollback` 全部保持不变；
10. 后续正常进入 HOME transfer。

## 强制契约

### `bulk_import.bin` 永远只读

无论 Apply、保存成功、保存失败、rollback、退出或重启，补丁都不得删除、改名、覆盖或写回：

```text
SD:/3ds/Bank/bulk_import.bin
```

如果文件继续存在，每次普通 game-linked Bank 下载完成后都会再次执行同一合并；是否移走由用户自己决定。

### `bulk_import.bin` 只提供 100 Box 数据

支持：

- `0xACA48`：PKHeX `Bank7` view；
- `0xBB518`：完整 Bank v1.5 image。

两种形式都只读取：

```text
0x00017C .. 0x0AAF14
```

即：

```text
100 × (
    30 × 0xE8 Pokémon
  + 0x26 Box metadata
)
```

bulk 中以下内容永远不是权威来源：

- slot format tag；
- source software；
- timestamp；
- Header / identity；
- Transfer Box；
- source summaries；
- NKZT；
- counters；
- tail；
- remote/session/transaction 数据。

## runtime 合并模型

```text
fresh server BankObject
        +
bulk main 100 Boxes
        +
stock-derived metadata context
        =
runtime candidate BankObject
```

### slot-aware writer

对每个槽比较 fresh server payload 与 bulk payload：

| 情况 | Pokémon payload | tag/source/timestamp |
|---|---|---|
| unchanged | 保留 server | 全部保留 server |
| empty -> occupied | 写 bulk | 生成当前联动游戏 metadata |
| occupied -> occupied changed | 写 bulk | 刷新当前联动游戏 metadata |
| occupied -> empty | 清 payload | 保留历史 server metadata |
| empty -> empty | 保持空 | 保留 server metadata |

其中 occupied -> empty 保留历史 metadata，符合真实 Bank 样本中“空槽仍残留 tag/source/timestamp”的观察。

## 原版 metadata 生成链

本实现不从 `bulk_import.bin` 复制 current-only metadata，而是复用对原版 `GameBank_SwapSelection` (`0x002B9C94`) 的逆向结论。

### 当前游戏 profile

```text
registry slot = 0x003AB90C
registry      = *(u32*)slot
model         = FUN_00233A6C(*(registry + 0x1C))
profile       = *(u8*)(model + 8)
```

profile：

```text
1 X
2 Y
3 Omega Ruby
4 Alpha Sapphire
5 Sun
6 Moon
7 Ultra Sun
8 Ultra Moon
```

### format tag

原版 profile 分支与现有真实样本一致：

```text
profile 1..4 -> tag 0
profile 5..8 -> tag 1
```

### source software

原版使用当前联动游戏的 source object，而不是 Pokémon 的 Origin Game：

```text
Gen6 profile 1..4: model + 0x129AC
Gen7 profile 5..8: model + 0x74304
```

然后调用该对象 vtable `+0x0C`（第 3 项函数）取得 `u8 sourceSoftware`。

### timestamp

沿用原版写 Bank slot metadata 的时间链：

```text
TIME_CONTAINER_INIT 0x00234648
TIME_QUERY          0x001D3BF4
TIME_PACK           0x001F2BD4
```

即：

```text
TIME_CONTAINER_INIT(temp)
TIME_QUERY(*(BankRoot + 0x138), temp)
timestamp = TIME_PACK(temp)
```

同一次 bulk apply 中 changed occupied slots 共用同一个 stock-derived timestamp，与原版批量 deposit 的行为一致。

## state 16 Hook 架构

不在 async success callback 中做 SD I/O。

### Hook 1：下载成功只设置 pending marker

位置：

```text
BankRemote_DownloadSuccessCallback + 0x14
= 0x002D11C4
```

Hook 保存寄存器和 CPSR，只检查：

```text
[r4 + 0x41]
```

只有普通 game-linked Bank 下载 (`== 0`) 才设置 pending byte。

HOME/full-transfer 回调不会设置 pending，因此 state 28 不会触发 bulk apply。

被覆盖的原版指令：

```asm
ldr r8, =0x000BB528
```

在 trampoline 末尾原样重放。

### Hook 2：下一次 BankDataSync update 执行 backup/apply

位置：

```text
BankDataSyncState_Update
= 0x002AF460
```

流程：

```text
replay native push {r4-r6,lr}
        ↓
读取 pending marker
        ↓
无 pending -> 直接回原版 +4
        ↓
有 pending -> 清 marker
        ↓
OfficialBulkSync_Process(state)
        ↓
回原版 BankDataSyncState_Update +4
```

因此网络回调返回以后才进行同步 SD I/O。

## fresh server 备份

在 Apply 之前写完整 `0xBB518`：

```text
SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

当前文件名的年月日时分来自 fresh Bank header，秒字段优先采用本次 stock timestamp 的秒值。

如果 backup 写入失败：

```text
不 Apply bulk
继续原版流程
```

如果 bulk streaming 过程中 short-read / I/O failure 且 runtime 可能已经部分修改：

```text
从刚写出的 timestamp backup 重新读取完整 0xBB518
恢复 fresh server BankObject
然后继续原版流程
```

`bulk_import.bin` 始终以 `OPEN_READ` 打开，没有任何 write/rename/delete 路径。

## official-only patch 边界

这个 feature 分支的默认构建不再使用旧 Route A Preview 的 Offline/Download UI。

实际只修改两个原版 Hook，以及两个经验证的全零 code cave：

```text
0x002AF460 .. 0x002AF464  BankDataSyncState_Update hook
0x002D11C4 .. 0x002D11C8  DownloadSuccess marker hook
0x00313910 .. 0x00314008  runtime adapter/code cave
0x003ABA90 .. 0x003ABFFC  merge core/code cave
```

pending scratch：

```text
0x003ABFFC
```

该字节只在运行期使用，静态 IPS 不写入它。

因此以下原版代码在当前构建中保持 byte-identical：

- 标题界面；
- Bank 菜单；
- 网络登录/认证；
- state 7 save transaction；
- `BankSave_SerializeAndStage`；
- `BankRemote_StageFileUpdate`；
- PrepareUpdate/HPP/CompleteUpdate；
- rollback；
- HOME state 28。

## 构建结构

新默认 Makefile：

```text
bank/src/Makefile
```

构建：

```text
official_bulk_sync.c
        -> official_bulk_sync.o

official_bulk_sync_core.c
        -> official_bulk_sync_core.o

main_official.s
        + 两个 object
        -> patched .code
        -> code.ips
```

旧 Scheme B / Offline-Download Preview 的构建规则保留在：

```text
bank/src/Makefile.route-a-preview
```

## 自动测试与静态验证

### host contract test

`official_bulk_sync_host_test.c` 覆盖：

- unchanged 保留 metadata；
- empty -> occupied 生成 metadata；
- occupied changed -> occupied 刷新 metadata；
- occupied -> empty 保留历史 metadata；
- Box metadata 来自 bulk；
- timestamp backup filename；
- Gen6/Gen7 profile -> format tag 映射。

### static verifier

`verify_official_bulk_sync.py` 会检查：

1. base SHA-256 必须是已确认的 Bank v1.5 `.code`；
2. 两个 code cave 在 base 中必须全零；
3. patched image 的每一个 changed byte 都必须落在四个允许区间；
4. pending scratch 静态仍为 0；
5. 关键符号地址一致；
6. `code.ips` 重放后必须逐字节得到 patched `.code`。

## 当前实现状态

已实现：

- D6A：official-only 原版联网入口；
- D6B：普通 Bank fresh download 后完整 timestamp backup；
- D6C：state 16 pending -> backup/apply；
- D6D：slot-aware metadata writer；
- D6E：stock save transaction 不打补丁；
- D6F：`bulk_import.bin` 强制只读；
- D6G：HOME/state 28 由 callback marker 条件排除。

仍待实机/服务器验证：

- D6H：官方 round-trip：1 -> 30 -> 300 -> 3000。

第一轮实机测试只能从 1 个 changed Pokémon 开始，保存成功后必须重新登录官方下载 server-after 做结构化 diff，再逐级扩大。
