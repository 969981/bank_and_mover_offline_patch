# Pokémon Bank Recovery C TechStable r3 使用说明

> 当前发布：**Official Bulk Sync V3 + Recovery C + C-only precise reconnect**。

## 安装

```text
SD:/luma/titles/00040000000C9B00/code.ips
```

Luma3DS 开启 `Enable game patching`。

只适用于 stock Bank v1.5：

```text
.code size  0x2AC000
SHA-256     2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

当前 r3 `code.ips`：

```text
size        1856 bytes
SHA-256     F5FCB3370D4CDC7521C9841BF61371FC2EFAEA7438E2546173B42F6353086A9D
```

## Recovery C r3：已锁存档怎么测

这次**可以保留**：

```text
SD:/3ds/Bank/bulk_import.bin
```

推荐流程：

```text
1. 先备份游戏存档
2. 安装 r3 code.ips
3. bulk_import.bin 保持原位
4. 用原来发生 Trainer/save mismatch 的同一游戏进入 Bank
5. Recovery C 从 CURRENT SERVER T1 重建 RAM recovery context
6. stock state17 做唯一一次 Rollback
7. stock 清 transactionPassword，并保存游戏 cleanup
8. r3 只对这次 C recovery 返回 result3
9. stock state20 clean disconnect/cleanup
10. 再次进入/重新联动同一游戏
11. 新 session 正常 BankDataSync 下载 fresh BankObject
12. Official Bulk Sync V3 读取 bulk_import.bin
13. 进入 Bank UI 检查 100 Box
14. 确认无误后使用原版 Bank 保存
15. 完全退出 Bank，再次进入验证 server round-trip
```

r3 的关键变化是：**不会在刚完成 Recovery C 的同一个 recovery session 里直接继续 Bulk。** Bulk 在下一次干净联动时执行。

## 关于“服务器被锁住”提示

第一次实机发现的：

```text
由于上次操作中断，因此服务器被锁住了。请稍后再试。
```

已经定位为 stock state17 initializer 的固定 message 0x0E，它在真正执行 Rollback/Commit 前就显示，因此不能单独作为“服务器仍然锁住”的证据。

r3 保留 stock UI helper，但将这条固定文案换成中性的连接/等待 message。

## r3 如何只影响 Recovery C

普通 stock recovery：

```text
status1 -> stock Rollback -> result4 -> state16
status2 -> stock Commit   -> result4 -> state16
```

Recovery C：

```text
state18 mismatch
→ RAM-only status3 marker
→ state17 入口识别 C marker
→ 立即恢复成 stock status1
→ stock Rollback/cleanup/save
→ C-only result3
→ state20 clean disconnect
```

status3 在任何 game save 前就恢复成 status1，不作为持久化格式使用。

## Bulk Sync

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

实际流程：

```text
fresh server BankObject
→ 自动完整备份到 SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
→ 只读 bulk_import.bin
→ slot-by-slot overlay 主 100 Box
→ 当前联动游戏生成 changed slot 的 tag/source/timestamp
→ Bank UI
→ 用户原版保存
```

注意：Bulk 是 overlay，不是 append；bulk 空槽代表对应 Bank Pokémon record 清空。宝可梦数据来源是 `bulk_import.bin`，不是自动读取当前游戏 PC Box。

## 当前验证状态

已通过 host、stock recovery model、Bulk regression、ARM build、armips link、机器码目标检查、真实 stock patch surface 和 IPS replay。

仍需这次实机确认：

```text
Recovery C -> clean disconnect
重新进入 -> Bulk Apply
原版保存 -> 完全退出 -> redownload
```
