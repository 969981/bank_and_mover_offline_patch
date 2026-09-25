# Pokémon Bank Recovery C — TechStable r3 / 方案 C

日期：2026-09-25  
Title ID：`00040000000C9B00`

当前 `code.ips` 同时包含：

```text
Official Bulk Sync V3
+
Recovery C Existing Lock Recovery
+
Recovery-C-only precise reconnect
```

## 安装

```text
SD:/luma/titles/00040000000C9B00/code.ips
```

Luma3DS 开启 `Enable game patching`。

严格版本：

```text
stock .code size  0x2AC000
stock SHA-256     2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

当前 r3：

```text
code.ips size     1856 bytes
code.ips SHA-256  F5FCB3370D4CDC7521C9841BF61371FC2EFAEA7438E2546173B42F6353086A9D
```

## Recovery C r3

针对已有 server pending transaction、而 game recovery `dataId/curVersion` mismatch 的锁存档：

```text
state18 mismatch
→ CURRENT SERVER T1 重建 RAM context
→ Recovery-C-only status3 marker
→ state17 入口立即还原成 stock status1
→ stock Rollback(T1)
→ stock clear transactionPassword
→ stock save cleanup
→ C-only result3
→ stock state20 clean disconnect
```

普通 stock state17 的 status1/status2 路径仍保持 `result4 → state16`，没有做全局路由改写。

status3 仅作 RAM marker，在任何 game save 前恢复为 status1，不作为持久化 recovery 格式。

第一次实机看到的“服务器被锁住”已经定位为 state17 initializer 在真正 RPC 前显示的固定 message 0x0E；r3 保留原 UI helper，只换成中性等待文案。

## bulk_import.bin 不需要移走

可以保留：

```text
SD:/3ds/Bank/bulk_import.bin
```

Recovery C 成功后会结束当前 recovery session。随后重新进入/重新联动时：

```text
fresh BankObject
→ Official Bulk Sync V3
→ bulk_import.bin 主 100 Box overlay
→ Bank UI 检查
→ 原版保存
```

Bulk 的 Pokémon 数据来源是 `bulk_import.bin`，不是自动抓取当前游戏 PC Box。Bulk 是 slot-by-slot overlay，不是 append。

## 实机测试顺序

```text
1. 备份游戏存档
2. 保留 bulk_import.bin
3. 安装 r3 code.ips
4. 进入原先锁住的游戏
5. 等 Recovery C Rollback/cleanup
6. 应进入 clean disconnect/返回边界，而不是同 session 继续 state16
7. 再次进入/重新联动同一游戏
8. 检查 Bulk Pokémon 是否出现在 Bank UI
9. 确认 Box 正确后原版保存
10. 完全退出，再进入验证服务器 round-trip
```

## 构建验证

```text
Recovery C host regression               PASS
stock recovery model regression          PASS
Official Bulk Sync regression            PASS
ARMv6K production build                  PASS
Windows armips link smoke                PASS
state18/state17 branch-target decode      PASS
critical machine-code assertions          PASS
real stock patch-surface replay           PASS
IPS replay == patched real stock image    PASS
RX tail                                   1771 / 1776 bytes
```

仍待真实锁存档 r3 端到端和网络 fault-injection，因此仍标记 **TechStable**。

详细文档：

```text
bank/docs/official-bank-existing-lock-recovery-techstable.zh-cn.md
bank/docs/official-bank-existing-lock-recovery-usage.zh-cn.md
bank/docs/official-bank-bulk-sync-principles-v3.zh-cn.md
```
