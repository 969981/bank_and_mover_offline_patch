# Official Bank Recovery A 实机验证指南

> 分支：`feature/official-bank-recovery-auto-rollback`
>
> 状态：`EXPERIMENTAL / HOST VERIFIED / IPS HOOK NOT YET EMITTED`

## 1. 目标

Variant A 的目标不是绕过所有 Trainer/save mismatch，而是仅在以下条件全部成立时自动走 stock Rollback：

```text
stock local recovery 不匹配
stock game recovery 不匹配
OBRX marker 已绑定真实 transaction
active profile 相同
marker 与当前 server pending transaction 全字段一致
```

恢复 record 由当前 server transaction 重建，并强制：

```text
status = 1
```

随后交回原版 Rollback 路径。

## 2. 当前已自动化验证

GitHub Actions `official-bank-recovery-a-ci` 覆盖：

- OBRX pending/bound marker；
- transaction 全字段 exact match；
- corrupt/pending-only/profile mismatch fail closed；
- auto-rollback policy；
- 48-byte marker persistence contract；
- runtime-neutral bulk→bind→mismatch→rollback record lifecycle；
- stock recovery decision model regression；
- Official Bulk Sync core regression。

## 3. 实机矩阵

### A0 正常保存

```text
bulk apply -> Prepare -> game save -> Complete success
```

预期：

- 不触发自动恢复；
- marker 最终清理；
- 下一次正常进入 Bank。

### A1 Prepare 前失败

预期：

- marker 最多停留 pending；
- pending-only marker 不允许自动 recovery；
- 原版行为保持。

### A2 已绑定 transaction 后网络失败

记录：

```text
profile
dataId
transactionPassword
curVersion
updateVersion
size
```

若下一次 stock state18 发生 mismatch，且 server tx 与 marker 完全一致：

```text
AUTO ROLLBACK
```

预期 Rollback 成功后重新进入 Bank，不再长期 Trainer/save lock。

### A3 任意字段不一致

分别修改/观察：

```text
profile
dataId
transactionPassword
curVersion
updateVersion
size
```

任一不一致预期：

```text
BLOCK -> stock mismatch
```

不得调用工具 Rollback。

### A4 server 已无 pending、marker 残留

预期只执行：

```text
LOCAL_CLEANUP
```

不得发送新的 Commit/Rollback。

### A5 普通手动 Game ↔ Bank 会话

无 OBRX exact bound marker 时，所有路径保持 stock。

## 4. 需要采集的证据

每次故障实验至少记录：

```text
Bank 错误文本
active profile
marker raw 48 bytes
server BankTransactionParam
pStatus / pApplicationId（若已 instrument）
stock local record 是否 match
stock game record 是否 match
工具最终 action
远端 Rollback 结果
下一次能否进入 state16 / Bank UI
```

## 5. 当前阻塞项

生成可安装 IPS 前还缺 verified stock `.code` 的机器码级证据：

- state7 transaction bind 的精确 ARM 指令边界；
- state18 mismatch edge 的精确 CMP/branch 地址及原始 bytes；
- Rollback success cleanup 的精确回调点；
- 可用 RX payload 空间验证。

目标 `.code`：

```text
size   = 0x2AC000
SHA256 = 2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

在这些 bytes 未验证前，不生成猜测地址的 IPS。
