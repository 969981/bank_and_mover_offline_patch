# Pokémon Bank Recovery C — TechStable

日期：2026-09-24  
Title ID：`00040000000C9B00`

## 这个 code.ips 包含什么

当前发布不是“只有 Recovery C”，而是：

```text
Official Bulk Sync V3
+
Recovery C / Existing Lock Recovery
```

因此安装本版后，同时具备：

1. 普通联动游戏进入 Bank 后，从 `SD:/3ds/Bank/bulk_import.bin` 将主 100 Box 数据合并到当前 fresh BankObject 的能力；
2. 对已经存在的 server pending transaction / Trainer-save mismatch 做 Rollback-only 解锁的能力。

---

## 安装

将：

```text
code.ips
```

放到：

```text
SD:/luma/titles/00040000000C9B00/code.ips
```

并确保 Luma3DS 已开启：

```text
Enable game patching
```

首次实机验证前建议备份相关游戏存档。

---

## Bulk Sync 快速使用

准备：

```text
SD:/3ds/Bank/bulk_import.bin
```

支持：

```text
0xACA48  PKHeX Bank7-compatible view
0xBB518  Bank v1.5 current image
```

操作：

```text
启动 Bank
→ 选择/联动一个受支持的 Pokémon 游戏
→ 原版 Bank 下载 fresh server BankObject
→ 自动备份 fresh BankObject
→ 自动读取 bulk_import.bin
→ 主 100 Box overlay 到 runtime BankObject
→ 进入 Bank UI 检查
→ 使用原版 Bank 保存
→ 原版上传到官方服务器
```

### 注意

这里的“联动游戏”不是把游戏存档里的全部 Pokémon 自动抓进 Bank。

实际数据源是：

```text
bulk_import.bin
```

当前联动游戏用于：

```text
普通 game-linked Bank 流程
generation/format tag
source software
timestamp
```

Bulk Apply 前会自动生成：

```text
SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

作为 fresh server BankObject 备份。

`bulk_import.bin` 始终只读，不会被删除、覆盖或改名。

---

## Recovery C 用途

Recovery C 用于 Pokémon Bank v1.5 已经存在 server pending transaction、但 stock state18 因 game recovery `dataId` / `curVersion` mismatch 而进入 Trainer/save mismatch 的恢复场景。

本版只做：

```text
Rollback
```

不会把未知历史 pending transaction Commit。

Recovery C：

- Hook `0x002A89D0`：game `dataId` mismatch；
- Hook `0x002A89E0`：game `curVersion` mismatch；
- 从当前 `[state18+0x28]` server transaction 重建 exact context；
- 重建内存中的 GameRecoveryRecord，设为 `status=1`；
- 交回 stock `state17`；
- 由原版 `RollbackBankObject` 做唯一一次远端 Rollback；
- 由 stock state17 清理 game transactionPassword 并保存。

不会：

- 自动 Commit 历史事务；
- 依赖 Recovery A / B；
- 使用 WAL；
- Hook 公共 invalid-status/error funnel；
- 修改 Pokémon box 正文。

---

## 已锁用户建议先这样测试

为了把 Recovery 和 Bulk 两个变量分开：

```text
1. 先备份游戏存档
2. 临时移走 SD:/3ds/Bank/bulk_import.bin
3. 安装 code.ips
4. 用原来 Trainer mismatch 的同一游戏进入 Bank
5. 验证 Rollback/cleanup
6. 完全退出 Bank
7. 再次进入确认锁已解除
8. 再把 bulk_import.bin 放回来测试 Bulk Sync
```

---

## 严格版本要求

仅适用于以下 stock Pokémon Bank `.code`：

- 大小：`0x2AC000`
- SHA-256：`2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`

不要用于其他 Bank 版本。

当前 `code.ips`：

- 大小：`1816` bytes
- SHA-256：`876955BF69FF600BFDEA0073B50F16CFE0CFFBA5275771BD5C951A0C30E3D09F`

---

## 构建验证

- Recovery C host regression：PASS
- stock recovery model regression：PASS
- Official Bulk Sync regression：PASS
- ARMv6K production object：PASS
- RX tail budget：`1741 / 1776 bytes`
- Windows armips link smoke：PASS
- `0x002A89D0` / `0x002A89E0` ARM BNE target：`0x00313934`
- IPS 仅覆盖三个 4-byte hook 与 `0x00313910..0x00314000` RX tail

---

## 当前验证边界

这是 **TechStable** 构建：代码、链接、机器码目标、空间预算和 host regression 已验证。

仍待继续实机验证：

- 已锁 Trainer mismatch 的真实 3DS 存档端到端恢复；
- Recovery 后重新进入同一存档；
- Bulk 1-slot → 保存 → redownload 官方 server round-trip；
- Recovery C + Bulk Sync 连续实机测试；
- Stage / game-save / cleanup 等网络 fault injection。

更完整技术说明见：

```text
bank/docs/official-bank-existing-lock-recovery-techstable.zh-cn.md
bank/docs/official-bank-existing-lock-recovery-usage.zh-cn.md
bank/docs/official-bank-bulk-sync-principles-v3.zh-cn.md
```
