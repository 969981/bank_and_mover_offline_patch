# Pokémon Bank Recovery C4 — Persistent Repair / TechStable

日期：2026-09-25  
Title ID：`00040000000C9B00`

当前 `code.ips` 同时包含：

```text
Official Bulk Sync V3
+
Recovery C4 Persistent Existing-Lock Repair
```

## 安装

```text
SD:/luma/titles/00040000000C9B00/code.ips
```

Luma3DS 开启 `Enable game patching`。

严格基线：

```text
stock .code size  0x2AC000
stock SHA-256     2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

当前 C4：

```text
code.ips size     1901 bytes
code.ips SHA-256  2C400AF5E0C5C997136A6C8F070B614D19A00A09339160A590AFDB684D3F8733
patched .code SHA-256
77ED66B94E0CC0619F6F52327CA2C1693536032F211E670459E57A842E8C7472
```

## C4 的恢复逻辑

针对 server 已有 pending transaction T1、而游戏 recovery 的 `dataId/curVersion` 不匹配：

```text
第一次进入
state18 mismatch
→ CURRENT SERVER T1 精确重建 GameRecoveryRecord
→ status3 仅作为 RAM handoff marker
→ state17 立即恢复成 stock status1
→ 跳过远端 Commit/Rollback
→ 保留 T1 transactionPassword
→ 调用 stock game-save writer 0x002B4AB4
→ exact T1/status1 真正写入游戏存档
→ 保存成功后 result3
→ state20 clean disconnect

第二次进入
游戏 recovery 与 server T1 匹配
→ 不再走原 mismatch edge
→ stock recovery
→ stock Rollback/cleanup
→ 正常 BankDataSync
```

第一轮若游戏保存失败，C4 不提前修改服务器 T1，继续走 stock error path。

## bulk_import.bin 可以保留

```text
SD:/3ds/Bank/bulk_import.bin
```

第一轮 C4 只修 recovery 存档，不执行 Bulk。服务器事务由下一次 stock recovery 正常完成后，普通 BankDataSync 下载 fresh BankObject，Bulk V3 才 Apply：

```text
fresh BankObject
→ Bulk Sync V3
→ bulk_import.bin 主 100 Box overlay
→ Bank UI
→ 原版保存
```

Bulk 是 overlay，不是 append；宝可梦数据来源仍是 `bulk_import.bin`。

## 关于“服务器被锁住”文案

stock state17 在真正恢复 RPC 前就会显示固定 recovery 提示，所以该文案本身不是服务器状态探针。C4 使用中性等待 message；真正要看的是第二次进入是否仍发生 transaction mismatch，以及能否走完 stock recovery。

## 实机测试顺序

```text
1. 备份相关游戏存档
2. 保留 bulk_import.bin
3. 安装 C4 code.ips
4. 第一次进入原来锁住的游戏
5. 等 C4 持久化 exact T1/status1 并结束本轮
6. 再次进入同一游戏
7. 观察 stock recovery 是否完成
8. 正常进入 BankDataSync 后检查 Bulk Pokémon
9. 确认 Box 正确后原版保存
10. 完全退出，再进入验证 server round-trip
```

## 构建验证

```text
TDD RED/GREEN                              PASS
Recovery C host regression                PASS
stock recovery model regression           PASS
Official Bulk Sync regression             PASS
ARMv6K production build                   PASS
Windows armips link smoke                 PASS
C4 stock save-call target 0x002B4AB4      PASS
state18/state17 branch-target decode       PASS
real stock patch-surface whitelist         PASS
IPS replay == patched real stock image     PASS
RX tail                                    1767 / 1776 bytes
```

真实锁存档 C4 端到端和 fault injection 仍待实机，因此仍标记 **TechStable**。

详细文档：

```text
bank/docs/official-bank-existing-lock-recovery-techstable.zh-cn.md
bank/docs/official-bank-existing-lock-recovery-usage.zh-cn.md
bank/docs/official-bank-bulk-sync-principles-v3.zh-cn.md
```