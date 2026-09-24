# Pokémon Bank Recovery C：TechStable 技术说明

> 分支：`feature/official-bank-existing-lock-recovery`
>
> 状态：**TechStable**
>
> 目标版本：Pokémon Bank v1.5，Title ID `00040000000C9B00`

## 1. 这版补丁实际上包含两套能力

当前 `code.ips` 不是单独的 Recovery C，而是：

```text
Official Bulk Sync V3
+
Recovery C / Existing Lock Recovery
```

两者共用同一个 RX text tail payload，但职责相互独立：

```text
Official Bulk Sync V3
    └─ 普通联动游戏进入 Bank 后
       读取 /3ds/Bank/bulk_import.bin
       将主 100 Box 数据 overlay 到 fresh runtime BankObject
       最终由原版 Bank 保存/上传

Recovery C
    └─ 已经存在 server pending transaction
       且 stock state18 因 recovery mismatch 被 Trainer/save error 锁住时
       只做安全 Rollback 解锁
```

因此，安装 Recovery C TechStable 后，**原先的 Official Bulk Sync V3 功能仍然保留**。

---

## 2. 严格适用基线

只适用于以下 stock Pokémon Bank `.code`：

```text
image base  0x00100000
size        0x2AC000
SHA-256     2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

不要应用到其它 Bank 版本。

当前发布 IPS：

```text
release/00040000000C9B00/code.ips
```

SHA-256：

```text
876955BF69FF600BFDEA0073B50F16CFE0CFFBA5275771BD5C951A0C30E3D09F
```

---

# Part A：Official Bulk Sync V3

## 3. Bulk Sync 的实际用户流程

运行流程：

```text
SD:/3ds/Bank/bulk_import.bin
        ↓
启动 Pokémon Bank
        ↓
选择并联动一个受支持的 Pokémon 游戏
        ↓
Bank 使用原版流程登录服务器
        ↓
Bank 下载当前账号 fresh BankObject
        ↓
BankDataSyncState 下载完成
        ↓
OfficialBulkSync_Process
        ↓
先备份 fresh BankObject
        ↓
读取 bulk_import.bin
        ↓
将主 100 Box overlay 到 runtime BankObject
        ↓
进入原版 Bank UI
        ↓
用户检查 Box
        ↓
用户按原版“保存”
        ↓
原版 PrepareUpdate / Upload / Complete
        ↓
官方服务器保存新的 BankObject
```

### 重要语义

“联动游戏 + Bulk Sync”表示：

- 宝可梦数据来源：`bulk_import.bin`；
- 当前联动游戏：作为普通 Bank 联动上下文，并提供当前写入 metadata；
- 目标：当前账号刚下载的 fresh BankObject；
- 最终持久化：仍然必须经过原版 Bank UI 的保存流程。

它**不是**：

```text
游戏存档 Box → 自动抓取全部 Pokémon → Bank
```

如果想把当前游戏里的宝可梦放进 Bank，仍然可以使用 Bank 原版界面操作；Bulk Sync 本身读取的是 `bulk_import.bin`。

---

## 4. bulk_import.bin 路径和格式

固定路径：

```text
SD:/3ds/Bank/bulk_import.bin
```

支持两种长度：

```text
0xACA48  PKHeX Bank7-compatible view
0xBB518  current Bank v1.5 image
```

Header 必须满足：

```text
version  = 2
boxCount = 100
```

Bulk 文件始终按只读方式打开：

```text
OPEN_READ
```

补丁不会删除、重命名、覆盖或写回 `bulk_import.bin`。

---

## 5. Bulk 实际复制哪些数据

Bulk 提供：

```text
100 Box
× 30 slots
× 0xE8 Pokémon record
+
每 Box 0x26 bytes Box metadata
```

不会整文件覆盖 fresh server BankObject。

以下 current/server 状态保留 fresh server base：

```text
Transfer Box
account/session-like fields
current-only summaries
NKZT/counters/tail
其它不属于主 100 Box overlay 范围的数据
```

这样做的核心是：

```text
fresh server BankObject
+
用户 bulk 主 Box 数据
+
stock-derived slot metadata
```

而不是：

```text
bulk 文件整包覆盖服务器对象
```

---

## 6. 联动游戏在 Bulk Sync 中到底负责什么

当前 active game model 用于生成发生变化槽位的：

```text
format tag
source software
timestamp
```

当前映射：

```text
profile 1..4 → format tag 0  （Gen 6-linked）
profile 5..8 → format tag 1  （Gen 7-linked）
```

`sourceSoftware` 直接调用当前联动软件的 stock source object getter。

`timestamp` 复用 Bank 自己的时间 helper。

因此从行为上看，Bulk 中新写入/替换的 Pokémon 会被标记为“在当前这次联动游戏上下文中写入 Bank”。

---

## 7. Slot-aware merge

每个 slot 会比较：

```text
fresh server slot
vs
bulk slot
```

### 完全相同

```text
Pokémon 不写
原来的 tag/source/timestamp 保留
```

### occupied → empty

```text
Pokémon record 清零
历史 slot metadata 保留
```

### empty → occupied

```text
写入 bulk Pokémon
写入当前 game format tag
写入当前 source software
写入当前 timestamp
```

### occupied → occupied changed

```text
替换 Pokémon
刷新当前 game format tag/source/timestamp
```

---

## 8. Fresh backup

在任何 Bulk overlay 之前，先备份刚从服务器下载的完整 current BankObject：

```text
SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

大小：

```text
0xBB518
```

只有 backup 成功后才允许 Apply Bulk。

如果 Bulk 中途读取失败，runtime 可能已经部分修改，则补丁会从刚写出的 backup 重新恢复 runtime body，避免带着半套数据进入 Bank UI。

---

## 9. 为什么必须最后在 Bank UI 手动保存

Bulk Sync 只修改内存里的 runtime BankObject，不 Hook 原版保存事务。

用户保存后仍走 stock：

```text
BankSaveState_Update
→ BankSave_SerializeAndStage
→ PrepareUpdateBankObject
→ HPP/HTTPS upload
→ CompleteUpdateBankObject
→ Commit
```

因此 `bulk_import.bin` 被 Apply 到 UI 中后，如果退出时不执行正常保存，服务器端不会因为 Bulk Sync 本身自动变更。

---

# Part B：Recovery C / Existing Lock Recovery

## 10. Recovery C 要解决的问题

典型锁死状态：

```text
官方服务器
已有 pending transaction T1
        ↓
Bank state18 已读到 T1
        ↓
local recovery / game recovery
与 T1 不一致
        ↓
stock 准备进入 Trainer/save mismatch
```

Recovery C 的固定职责：

```text
只解除已有 pending T1
只使用 Rollback
不尝试历史 Commit
```

---

## 11. 精确 Hook

保留 Bulk Sync 的原 hook：

```text
0x002AF460
BankDataSyncState_Update
→ OfficialBulk_BankDataSyncDispatch
```

Recovery C 只额外修改：

```text
0x002A89D0  game dataId mismatch
0x002A89E0  game curVersion mismatch
```

两条 branch 都跳到：

```text
0x00313934 OfficialExistingLock_GameMismatch
```

没有 Hook：

```text
0x002A8AD0 shared mismatch/error funnel
invalid status branches
normal matching recovery path
```

---

## 12. Recovery C 运行时链

```text
state18
  ↓
local recovery 没有完成恢复
  ↓
game recovery dataId / curVersion mismatch
  ↓
Recovery C
  ↓
读取 [state18+0x28]
CURRENT SERVER BankTransactionParam T1
  ↓
复制完整 T1 到 state18 canonical runtime context
  ↓
重建当前内存 GameRecoveryRecord
  dataId = T1.dataId
  transactionPassword = T1.transactionPassword
  curVersion = T1.curVersion
  updateVersion = T1.updateVersion
  size = T1.size
  status = 1
  ↓
标记 source = game
  ↓
stock state18 正常完成
  ↓
result=4 → stock state17
  ↓
state17 读取 status=1
  ↓
stock RollbackBankObject(T1)
  ↓
远端 pending T1 被回滚
  ↓
stock 清 game recovery transactionPassword
  ↓
stock game save writer 持久化 cleanup
```

关键点：

> Recovery C 本身不重新实现 Nintendo 的远端事务协议，真正的远端 Rollback 与 game cleanup 仍由 stock state17 执行。

---

## 13. 为什么不能在 state18 直接 Rollback 然后照常进 state17

已确认：

```text
state18 result 4 → state17
```

而 state17 会重新读取 GameRecoveryRecord：

```text
status=1 → Rollback
status=2 → Commit
```

如果在 state18 直接强制 Rollback，但 stale game recovery 仍是：

```text
status=2
transactionPassword != 0
```

会出现：

```text
state18 Rollback
→ state17
→ stale status=2
→ Commit
```

Recovery C 因此采用“重建 exact T1 的 game recovery + status=1，再交给 stock state17”的链路，保证远端 Rollback 只发生一次。

---

## 14. Recovery C 明确不会做什么

不会：

- Commit 历史 pending transaction；
- 根据 stale local/game recovery 猜测哪次事务应该 Commit；
- 依赖 Recovery A / B；
- 依赖 WAL；
- 要求用户在锁死之前已经安装补丁；
- NOP Trainer mismatch；
- 修改 Pokémon Box 正文；
- 自己重写 NEX / HPP / Complete / Rollback 网络协议。

---

# Part C：组合后的代码布局

## 15. RX tail

唯一 executable payload 仍限制在：

```text
0x00313910 .. 0x00314000
```

预算：

```text
Bulk payload       1577 bytes
ARM dispatcher       36 bytes
Recovery C shim     128 bytes
--------------------------------
Total              1741 / 1776 bytes
Remain               35 bytes
```

不使用 mapped `.data/BSS` 作为 code cave。

---

## 16. 组合功能之间的关系

正常用户进入 Bank：

```text
普通游戏联动下载完成
→ Bulk Sync gate
→ 有合法 bulk_import.bin：Apply
→ 没有 bulk_import.bin：什么都不做
→ Bank UI
```

已有 Trainer mismatch 锁用户：

```text
登录 recovery state18
→ 命中真实 game mismatch
→ Recovery C Rollback 解锁
```

因此：

```text
Bulk Sync = 正常联动后的 Box 数据导入能力
Recovery C = 异常 pending transaction 的已有锁恢复能力
```

二者不会把 Bulk 导入本身当成 Recovery C 的 Commit 依据。

---

## 17. 当前验证状态

已验证：

```text
Recovery C host regression          PASS
stock recovery model regression     PASS
Official Bulk Sync host regression  PASS
ARMv6K production objects           PASS
RX tail budget                      PASS
Windows armips link smoke           PASS
Recovery C ARM branch decode        PASS
IPS patch surface whitelist         PASS
```

仍待实机：

```text
真实已锁 Trainer mismatch 存档端到端恢复
Recovery 后再次进入同一存档
异常网络 fault injection
Recovery C + Bulk Sync 同一台实机连续 round-trip
```

因此发布状态称为 **TechStable**，而不是最终 hardware-verified Stable。
