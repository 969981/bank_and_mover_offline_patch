# Pokémon Bank Recovery C — TechStable

日期：2026-09-24  
Title ID：`00040000000C9B00`  
生产代码基线提交：`d269d20a31d26993a28767aa0dba4aaca563dd97`

## 用途

Recovery C 用于 Pokémon Bank v1.5 已经存在 server pending transaction、但 stock state18 因 game recovery `dataId` / `curVersion` mismatch 而进入 Trainer/save mismatch 的恢复场景。

本版只做 **Rollback**，不会把历史 pending transaction Commit。

## 安装

将：

`luma/titles/00040000000C9B00/code.ips`

复制到 SD 卡相同路径，并确保 Luma3DS 已开启 **Enable game patching**。

首次实机验证前请备份游戏存档与 Bank 相关数据。

## 严格版本要求

仅适用于以下 stock Pokémon Bank `.code`：

- 大小：`0x2AC000`
- SHA-256：`2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`

不要用于其他 Bank 版本。

## Recovery C 行为

- Hook `0x002A89D0`：game `dataId` mismatch
- Hook `0x002A89E0`：game `curVersion` mismatch
- 从当前 `[state18+0x28]` server transaction 重建 canonical context
- 重建内存中的 GameRecoveryRecord，并设为 `status=1`
- 交回 stock `state17`
- 由原版 `RollbackBankObject` 执行唯一一次远端 Rollback
- 由 stock state17 清理 game transactionPassword 并保存

不会：
- 自动 Commit 历史事务
- 依赖 Recovery A / B
- 使用 WAL
- Hook 公共 invalid-status/error funnel
- 修改 Pokémon box 正文

## 构建验证

- Recovery C host regression：PASS
- stock recovery model regression：PASS
- existing Bulk regression：PASS
- ARMv6K production object：PASS
- RX tail budget：`1741 / 1776 bytes`
- Windows armips link smoke：PASS
- `0x002A89D0` / `0x002A89E0` ARM BNE target 解码：均为 `0x00313934`
- IPS 记录仅覆盖三个 4-byte hook 与 `0x00313910..0x00314000` RX tail

`code.ips`：
- 大小：`1816` bytes
- SHA-256：`876955BF69FF600BFDEA0073B50F16CFE0CFFBA5275771BD5C951A0C30E3D09F`

## 当前验证边界

这是 **TechStable** 构建：代码、链接、机器码目标、空间预算和 host regression 已验证。

仍待：
- 已锁 Trainer mismatch 的真实 3DS 存档端到端测试
- Stage / game-save / cleanup 等网络故障窗口的实机 fault injection

因此第一次使用仍建议在可恢复备份上进行。
