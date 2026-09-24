# Pokémon Bank Recovery C TechStable 使用说明

> 本说明面向实际安装和验证。
>
> 当前发布同时包含：**Official Bulk Sync V3 + Recovery C**。

## 1. 安装

目标 Title ID：

```text
00040000000C9B00
```

将发布文件：

```text
release/00040000000C9B00/code.ips
```

放到 SD 卡：

```text
SD:/luma/titles/00040000000C9B00/code.ips
```

Luma3DS 必须启用：

```text
Enable game patching
```

第一次测试前建议备份相关游戏存档。

---

## 2. Bulk Sync：把 bulk_import.bin 的宝可梦导入 Bank

### 2.1 准备文件

固定输入路径：

```text
SD:/3ds/Bank/bulk_import.bin
```

支持：

```text
0xACA48  PKHeX Bank7-compatible view
0xBB518  Bank v1.5 current image
```

文件必须是：

```text
version  = 2
boxCount = 100
```

### 2.2 操作顺序

```text
1. 把 bulk_import.bin 放到 SD:/3ds/Bank/
2. 启动 Pokémon Bank
3. 选择/联动一个受支持的 Pokémon 游戏
4. 等待 Bank 正常下载当前服务器 Bank 数据
5. Bulk Sync 自动备份 fresh BankObject
6. Bulk Sync 自动把 bulk_import.bin 的主 100 Box 合并进 Bank 内存数据
7. 进入 Bank UI 后检查 Box 内容
8. 使用 Bank 原版“保存”功能
9. 让原版 Prepare / Upload / Complete 流程完成
10. 重新进入 Bank 验证服务器 round-trip
```

### 2.3 “联动游戏”的准确含义

这项功能是：

```text
bulk_import.bin 中的 Pokémon
        ↓
当前联动游戏提供 Bank 普通联动环境和 metadata 来源
        ↓
fresh server BankObject
        ↓
Bank UI
        ↓
原版保存到服务器
```

不是：

```text
当前游戏存档全部 Pokémon → 自动复制到 Bank
```

Bulk 中宝可梦的来源仍是 `bulk_import.bin`。

当前联动游戏主要用于：

- 进入普通 game-linked Bank 下载路径；
- 提供当前 `format tag`；
- 提供当前 `source software`；
- 提供 stock runtime timestamp。

### 2.4 自动备份

每次真正 Apply Bulk 之前会先生成：

```text
SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

这是刚从服务器下载、尚未被 Bulk 修改的 fresh BankObject，大小：

```text
0xBB518
```

如果 backup 失败，Bulk 不会 Apply。

如果 Bulk 读取到一半发生 I/O 错误，会尝试把刚生成的 backup 重新恢复到 runtime BankObject。

### 2.5 bulk_import.bin 不会被修改

补丁只读：

```text
SD:/3ds/Bank/bulk_import.bin
```

不会自动：

- 删除；
- 改名；
- 移走；
- 覆盖；
- 写回 metadata。

因此如果文件一直留在该路径，下次普通联动成功后仍会再次进入 Bulk merge 检查。

已经与服务器完全相同的 slot 不会重复刷新 metadata。

---

## 3. Recovery C：处理已经出现的 Trainer/save mismatch

适用情形：

```text
服务器已经存在 pending transaction T1
+
当前 local/game recovery 与 T1 不一致
+
stock Bank state18 即将进入 Trainer/save mismatch
```

Recovery C 会：

```text
读取当前 server T1
→ 重建 exact game recovery context
→ 强制 status=1 / Rollback
→ 交回 stock state17
→ stock RollbackBankObject(T1)
→ stock 清理 game recovery transactionPassword
→ stock 保存 cleanup
```

不会尝试把未知历史 transaction Commit。

---

## 4. 已锁用户建议验证顺序

```text
1. 先备份游戏存档
2. 暂时移走 SD:/3ds/Bank/bulk_import.bin
3. 安装 Recovery C code.ips
4. 用发生 Trainer mismatch 的同一游戏进入 Bank
5. 确认 Recovery C 完成 Rollback/cleanup
6. 完全退出 Bank
7. 再次进入同一游戏验证锁是否消失
8. 确认正常 Bank 浏览/保存功能
9. 再放回 bulk_import.bin 测试 Bulk Sync
```

把 Recovery 测试和 Bulk 数据变更测试分两次做，更容易判断问题来源。

---

## 5. Bulk Sync 建议验证顺序

不要第一次就直接 3000 只全量覆盖。

推荐：

```text
H0：不放 bulk_import.bin，确认普通 Bank 完全正常
H1：只改 1 个 slot
H2：重新登录确认 server round-trip
H3：扩大到 1 Box / 30 slots
H4：扩大到多 Box
H5：最终再做全 100 Box
```

每一步都保留自动生成的 fresh backup。

---

## 6. 版本限制

仅适用于 stock Pokémon Bank v1.5：

```text
.code size  0x2AC000
SHA-256     2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

当前 `code.ips`：

```text
SHA-256 876955BF69FF600BFDEA0073B50F16CFE0CFFBA5275771BD5C951A0C30E3D09F
```

---

## 7. 当前状态

当前称为 **TechStable**：

已经通过：

- host regression；
- stock recovery model regression；
- Bulk Sync regression；
- ARMv6K production build；
- RX-tail budget；
- armips link smoke；
- Recovery C branch target decode；
- IPS patch-surface whitelist。

仍建议继续补：

- 真实 Trainer mismatch 锁存档恢复；
- Recovery 后再次进入 Bank；
- Bulk 1-slot → server save → redownload；
- Recovery C 与 Bulk Sync 连续实机测试；
- 网络故障 fault injection。
