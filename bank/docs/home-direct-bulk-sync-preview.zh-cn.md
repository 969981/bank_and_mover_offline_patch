# Pokémon Bank v1.5 HOME Direct Bulk Sync Preview

> 分支：`feature/home-direct-bulk-sync`
>
> 基线：`feature/official-bank-bulk-sync`
>
> 状态：开发预览；完成静态/CI 验证后仍必须做真实 Bank/HOME 小样本验证。

## 1. 目标

把原来必须经由 Gen6/Gen7 游戏联动触发的 `bulk_import.bin` 合并，扩展到 Pokémon HOME 迁移入口：

```text
bulk_import.bin
  → Bank 主菜单选择 Pokémon HOME
  → State 28 下载 fresh server BankObject
  → 本地备份 + bulk merge
  → State 29 使用原版远端 job 提交更新
  → State 27 保持原版 HOME Moving Key / box migration
```

不修改 HOME 的 Moving Key、box list、`RequestMigration`、`GetMigrationStatus` 逻辑。

## 2. 原版状态边界

HOME 路径：

```text
State 28  0x002AF460  完整 BankObject 下载
State 29  0x002AFE94  远端事务释放/rollback
State 27  0x002A7BF0  HOME 迁移 UI 与请求
```

普通联动 Bank 与 HOME 都使用 `0x002AF460`，区别为 state `+0x41` 模式字节：普通 Bank 为 0，HOME 为 1。

本分支保留 State 27 byte-identical，只在 State 28 和 State 29 增加有条件的 adapter。

## 3. State 28：HOME bulk apply

完成原版下载后：

1. 验证运行时 BankObject 和 `0xBB518` header；
2. 写 `SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin` fresh snapshot；
3. 只读打开 `SD:/3ds/Bank/bulk_import.bin`；
4. 合并主 100 Box Pokémon payload 与 Box metadata；
5. 成功发生 HOME bulk 修改后设置 `HOME_BULK_DIRTY=1`。

普通 game-linked State 16 继续使用原有 selected-game metadata 链。

## 4. HOME metadata 策略

HOME 路径没有当前联动游戏，因此不能调用 selected-game profile 生成 source metadata。

当前 preview 策略：

- changed occupied slot：写 bulk Pokémon payload；`tag=1`（Bank7/Gen7 记录格式）；保留 fresh server `sourceSoftware/timestamp`；
- empty → occupied：写 payload；`tag=1`；fresh server source/time 本来为空则保持 0；
- occupied → empty：清 payload；保留历史 tag/source/timestamp；
- unchanged：全部保留 fresh server；
- Box metadata：来自 bulk；
- header / identity / Transfer Box / counters / remote state：不从 bulk 覆盖。

这避免伪造一个并不存在的“当前联动游戏”。

## 5. State 29：official commit gate

State 29 原版 substate 0 仍然原样创建远端 job。只有 `HOME_BULK_DIRTY=1` 且原版进入 substate 1 时，补丁才接管：

```text
serialize runtime BankObject (0xBB518)
  → BankRemote_StageFileUpdate / 0x002A2504
  → 等待 stock callback
  → BankRemote_CommitStagedUpdate / 0x001D5D74
  → 等待 stock callback
  → 成功：清 dirty，送到 State29 stock success terminal
  → State27
```

### 失败

Stage/Commit 任一步失败：

```text
HOME_BULK_DIRTY = 2
State29 substate = 1
  → 回落原版 State29
  → 原版 0x001D5C28 rollback
  → rollback callback
  → 强制进入 State29 stock error terminal
```

因此失败时不会进入 State 27，不会对 HOME 发起迁移。

## 6. 为什么不 Hook State 27

`RequestMigration` 不是 BankObject 上传接口。把 bulk 只留在内存里然后进入 State 27，不能证明 HOME 服务器会读取本地修改后的 `0xBB518`。

因此必须在 State 27 之前完成服务器 BankObject 的官方更新事务；State 27 本身保持原版，可以继续使用官方 Moving Key、box selection 与 migration status handling。

## 7. Hook 范围

预览版新增的静态修改范围应仅包括：

```text
0x002AF460 .. 0x002AF464  State16/28 download adapter
0x002AFE94 .. 0x002AFE98  State29 commit gate
0x00313910 .. 0x00314000  RX text tail payload
```

映射 `.data` 镜像不允许静态修改。`0x003ABFF8/0x003ABFFC` 仅作为运行时 scratch（buffer pointer / dirty state）。

## 8. 测试门槛

### 自动验证

必须同时通过：

- host merge contract；
- State16 / State28 gating；
- State29 Stage/Commit/stock rollback contract；
- ARMv6K Thumb `-Werror`；
- 禁止 `__aeabi_*div*` runtime helper；
- 禁止旧 Thumb→ARM external helper relocation；
- RX text-tail size budget；
- 最终 IPS changed-byte allowlist；
- `.data` byte-for-byte unchanged；
- IPS replay == patched `.code`。

### 实机/服务器验证

第一轮只允许：

```text
1 个 changed Pokémon
1 个 HOME box
```

顺序：

```text
1. 准备 bulk_import.bin，仅改 1 个槽
2. 进入 Bank → Pokémon HOME
3. 确认 fresh timestamp backup 已生成
4. 等 State28 apply + State29 official commit 完成
5. 进入 State27 后只选择目标 Box
6. 输入 HOME Moving Key
7. HOME 接收后核对 Pokémon
8. 再次登录 Bank 下载 server-after
9. 对 before / bulk / server-after 做结构化 diff
```

确认 1 个槽 round-trip 后再扩大到 30 → 300 → 3000。

## 9. 发布等级

在真实服务器与 HOME round-trip 完成前，只能发布为：

```text
PREVIEW / EXPERIMENTAL
```

不能标为 stable，也不能把“CI 通过”描述成“HOME 迁移已实机验证”。
