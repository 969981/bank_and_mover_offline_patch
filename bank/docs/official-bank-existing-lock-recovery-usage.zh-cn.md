# Pokémon Bank Recovery C4 TechStable 使用说明

> 当前发布：**Official Bulk Sync V3 + Recovery C4 Persistent Repair**。

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
```

## 已锁存档的实机流程

`bulk_import.bin` **可以保持原位**：

```text
SD:/3ds/Bank/bulk_import.bin
```

建议先备份游戏存档，然后按两阶段理解 C4：

```text
第一次进入
1. 用原先发生 Trainer/save mismatch 的同一游戏进入 Bank
2. C4 读取 CURRENT SERVER pending T1
3. 用 T1 精确重建 GameRecoveryRecord
4. RAM-only status3 被 state17 立即转换成 stock status1
5. 第一轮不发 Commit，也不发 Rollback
6. 调用 Bank 原版游戏保存器，把 exact T1/status1 真正写进游戏存档
7. 保存成功后 result3 -> state20 clean disconnect

第二次进入
8. 再次进入/重新联动同一游戏
9. 游戏存档 recovery 此时应与 server T1 匹配
10. 不再命中原来的 dataId/curVersion mismatch
11. 完全交给 stock recovery 做 Rollback/cleanup
12. 服务器 pending T1 被原版流程处理
13. 恢复正常 BankDataSync 后，Official Bulk Sync V3 才读取 bulk_import.bin
14. 进入 Bank UI 检查 Box
15. 确认无误后使用原版 Bank 保存
16. 完全退出，再次进入确认 server round-trip
```

## C4 与 r3 的关键区别

r3 仍是在同一次运行中根据 RAM 合成记录进入远端 recovery。C4 改成：

```text
先修游戏存档
→ 再结束当前 session
→ 下一次完全走 stock server recovery
```

因此第一轮如果游戏保存失败，C4 不伪造成功，也不会提前修改服务器 pending T1；仍走 stock error path，属于 fail-closed。

## 关于“服务器被锁住”提示

stock state17 initializer 在真正执行 Commit/Rollback 之前就会显示 recovery 提示，因此这句话不能单独作为“服务器当前仍有锁”的探针。

C4 仍使用中性 message id。判断修复是否成功，应看第二次进入时是否还发生同一个 transaction mismatch，以及是否能进入 stock matching recovery/正常 BankDataSync。

## Bulk Sync V3

固定输入：

```text
SD:/3ds/Bank/bulk_import.bin
```

支持：

```text
0xACA48  PKHeX Bank7-compatible view
0xBB518  Bank v1.5 current image
```

要求：

```text
version=2
boxCount=100
```

Bulk 仍是：

```text
fresh server BankObject
→ 自动备份 bankdata_YYYYMMDD_HHMMSS.bin
→ 只读 bulk_import.bin
→ slot-by-slot overlay 主 100 Box
→ Bank UI
→ 用户原版保存
```

Bulk 是 overlay，不是 append；宝可梦数据来源是 `bulk_import.bin`，不是自动读取当前游戏 PC Box。

## 当前验证状态

代码侧已通过：TDD RED/GREEN、Recovery C host regression、stock recovery model、Bulk regression、ARMv6K build、Windows armips link、C4 save-call target `0x002B4AB4`、真实 stock patch-surface whitelist、IPS replay。

RX tail：

```text
1767 / 1776 bytes
remain 9 bytes
```

仍需本次真实 3DS 验证：第一轮是否成功持久化 exact T1、第二轮是否进入 stock recovery 并清掉 server pending T1、随后 Bulk 是否正常 round-trip。因此仍标记 **TechStable**。