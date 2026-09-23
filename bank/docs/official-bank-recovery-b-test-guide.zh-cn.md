# Official Bank Recovery B：Bulk-only Smart Commit / Rollback 实机验证指南

> 分支：`feature/official-bank-recovery-smart`
>
> 状态：`EXPERIMENTAL / CIA + MACHINE-CODE + PRODUCTION-LINK CI VERIFIED / HARDWARE FAULT TEST PENDING`

## 1. 最终目标

B 与 A 一样，首先关闭最危险的事务窗口：

```text
server pending 已经建立
但 local/game recovery 尚未 durable
```

区别是 B 不满足于“一律回滚”。它会利用原版游戏存档中已经持久化的 `GameRecoveryRecord status=2` 作为 **Commit 正证据**：

```text
没有 durable game Commit 证据 -> Rollback
有 exact durable game status=2 -> Commit
```

但只有在能证明 server pending transaction 确实属于我们此前写下的 pre-RMC52 WAL 时，B 才允许自动修复；foreign/stale record 不获得权限。

## 2. Bank v1.5 事务事实

验证基线：

```text
Title ID      00040000000C9B00
.code size    0x2AC000
SHA-256       2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

真正 Stage 前：

```asm
0x002B2494  LDR r3,[r4,#0x28]   ; exact BankTransactionParam*
0x002B2498  LDRD r0,r1,[r4,#0x40]
0x002B249C  MOV r2,r11
0x002B24A0  BL  0x002A2504      ; Stage / RMC52
```

因此 `state+0x28` 在服务器 pending 建立前已经完整可用，可以先做 durable write-ahead journal。

## 3. Bulk-only gate

B 与 A 共用运行时 scratch：

```text
0x003ABFFC  BulkSessionFlag
```

规则：

```text
state16 substate 0       -> flag = 0
bulk apply 真正成功       -> flag = 1
普通 Bank save           -> flag = 0，完全 stock
pre-RMC52 WAL 已 durable  -> flag = 0，再开始 Stage
```

因此 B 不再修改普通非 Bulk Bank 会话。

## 4. 为什么 B 使用私有 status=3

A 可以直接借用原版 `status=1`，因为 A 的目标就是安全 Rollback。

B 必须区分两件事：

```text
stock status=1
= 原版本来就已经决定应该 Rollback

private status=3
= 我们只知道“这是 pre-RMC52 durable fallback”
  但仍应先查看 game recovery，判断是否已有 Commit 正证据
```

所以 B 在 Bulk session 的 pre-journal pass 中，Hook stock case7 status immediate：

```text
0x002B1FFC
stock:   status = 1
private: status = 3   （仅 journal pass）
```

普通 case7 仍保持 `status=1`。

## 5. Pre-RMC52 durable WAL

Production hooks：

```text
0x002B1DE4  save case1
0x002B1FFC  private status selector
0x002B2090  local-save result
```

第一次进入 case1 且 `BulkSessionFlag=1`：

```text
切到 stock case7
        ↓
把 state+0x28 exact BankTransactionParam
写入 Bank-local RecoveryRecord
status = 3
        ↓
stock local save
```

local save 成功后：

```text
回到 case1
清临时 journal marker
清 BulkSessionFlag
        ↓
才执行原版 SerializeAndStage / RMC52
```

local save 失败则不发 RMC52。

因此 server 只要能留下 pending，本地一定先有一份 durable status3 exact WAL。

## 6. state18 ownership validation

### 6.1 stock 已先验证 dataId + curVersion

B Hook：

```text
0x002A8968  local status decision
```

只有 `status=3` 才进入私有 WAL 路径。

由于 stock 在到达这里前已经验证：

```text
server.dataId == local.dataId
server.curVersion == local.curVersion
```

B 再补齐：

```text
updateVersion
size
transactionPassword low/high
```

全部一致才视为：

> 当前 server pending tx 就是这份 private WAL 对应的事务。

如果任一字段不一致，则不授权 Commit/Rollback，回到保守的 stock game validation / error 路径。

### 6.2 exact private WAL 后先检查 game record

exact WAL 成立后：

```text
state+0x88 = 2   ; trusted rollback fallback available
进入 stock game recovery check
```

若当前游戏 recovery exact 且：

```text
status=2
```

则走原版 Commit。

B 不伪造 transactionPassword，也不自己实现远端 Commit；只是让 stock recovery 使用已经存在的 durable game evidence。

## 7. game mismatch / invalid game evidence

真正 game mismatch branches：

```asm
0x002A89D0  BNE   ; dataId mismatch
0x002A89E0  BNE   ; curVersion mismatch
```

B 只 Hook 这两个真实 mismatch edge，不 Hook 公共错误 funnel。

同时复用 stock 的冗余小块：

```text
0x002A8A64..0x002A8A7C
```

作为 in-place decision：

```text
state+0x88 == 2
    -> trusted exact private WAL exists
    -> game 没有可靠 status2 Commit 证据
    -> stock Rollback substate 6

否则
    -> stock mismatch/error substate 8
```

因此真实不同存档、foreign transaction、stale WAL 不会因为本补丁而被强行放行。

## 8. B 的 production hook map

最终允许修改：

```text
0x002AF460  Official Bulk state16 hook

0x002B1DE4  pre-RMC52 journal entry
0x002B1FFC  journal-only private status selector
0x002B2090  journal local-save result

0x002A8968  local status3 ownership decision
0x002A89D0  game dataId mismatch edge
0x002A89E0  game curVersion mismatch edge
0x002A8A64..0x002A8A7C  in-place smart fallback block

0x00313910..0x00314000  RX-tail payload
```

其它 `.code` 字节必须保持 stock。

## 9. A / B 的最终区别

| 场景 | A | B |
|---|---|---|
| 非 Bulk 普通 Bank save | stock | stock |
| Stage 前 | durable native status1 WAL | durable private status3 WAL |
| server pending、game 尚无 durable recovery | Rollback | Rollback |
| game exact status2 已 durable、Complete 未成功 | stock 状态决定；不主动智能 Commit | **Commit** |
| private/local WAL 与 server tx 不 exact | stock protection | stock protection |
| game mismatch 且无 trusted WAL | stock error | stock error |
| game mismatch + exact trusted WAL | A 依靠 stock status1 Rollback | **Rollback** |

B 的价值在于：既消除 pending-without-recovery 锁死窗口，又尽量保住已经真正落入游戏存档的事务。

## 10. RX-tail / production build

唯一大 RX cave：

```text
0x00313910..0x00314000
0x6F0 = 1776 bytes
```

CI 不再硬编码历史对象大小，而是实际编译：

```text
arm-none-eabi-gcc official_bulk_sync_prod.c
arm-none-eabi-as  official_recovery_wal_thumb.s
TOTAL = bulk + 36-byte ARM dispatcher + WAL
TOTAL <= 1776
```

并额外进行 production-object smoke：

```text
Linux 编译真实 GCC/as ELF objects
        ↓
Windows 下载真实 objects
        ↓
armips 实际组装 main_official.s
        ↓
检查所有 hook / symbols / RX-tail layout
```

这套 smoke 已经真实发现并修复过一次 `__aeabi_lmul` 未链接问题；因此现在不是只靠假的 stub 验证接口。

## 11. 最终静态安全门

release verifier 要求：

- stock SHA 精确匹配；
- 仅允许第 8 节列出的 hook 区域 + RX tail 变化；
- `0x0036A000..0x003AC000` mapped data image 完全不变；
- WAL/Bulk symbols 必须全部位于 RX tail；
- IPS replay 必须逐字节重建 patched `.code`。

## 12. 实机 fault-injection 矩阵

重点测试：

1. **普通非 Bulk Bank save**：必须完全表现为 stock；
2. pre-journal local save 失败：不得发 Stage；
3. WAL durable 后、Stage 失败：不得产生错误 Commit；
4. Stage 成功、game recovery 未 durable：exact private WAL -> Rollback；
5. game save 中途失败：Rollback；
6. game main 已 durable、local 后续状态尚未完成、Complete 网络失败：game exact status2 -> **Commit**；
7. local/game 都已有 stock status2：stock Commit；
8. foreign/stale status3 WAL：不得自动 Commit/Rollback；
9. 真实不同存档：保持 stock mismatch/error。

每次记录：

```text
server pStatus / BankTransactionParam
local recovery dataId / curVersion / updateVersion / size / password / status
game recovery dataId / curVersion / status
state+0x88 trusted-fallback flag
最终 Commit / Rollback
下一次是否能正常进入 Bank
Bulk 数据是否保留
游戏 main 是否一致
```

B 的实机验收标准：

> **Bulk 保存网络异常不能再因为 server pending 与 durable recovery 脱节而永久锁死；只有存在 exact、durable game status=2 正证据时才保留事务，否则安全 Rollback。**
