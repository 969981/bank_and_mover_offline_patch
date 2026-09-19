# Pokémon Bank v1.5 Official Bulk Sync V3 使用文档

> 分支：`feature/official-bank-bulk-sync`
>
> 当前发布：`official-bulk-sync-v3-preview-20260919`
>
> V3 是实验性 prerelease。当前已完成静态/CI 验证以及前两轮实机故障定位修复；**官方服务器 Save → 退出 → 移走 bulk → 重新下载的 round-trip 仍应从 1 只 Pokémon 开始验证。**

---

## 1. V3 是什么

V3 不再提供用户可见的 Offline Mode / Download Mode。安装后仍按 Pokémon Bank 原版流程使用：

```text
启动 Pokémon Bank
→ 原版联网/登录
→ 原版选择任意支持的 Gen6 / Gen7 游戏
→ 原版下载官方 BankObject
→ V3 先备份 fresh server Bank
→ V3 读取 /3ds/Bank/bulk_import.bin
→ V3 把 bulk 的主 100 Box 合并进 runtime BankObject
→ 原版 Bank Box UI
→ 用户人工检查
→ 用户选择原版保存
→ 原版 PrepareUpdate / HPP / CompleteUpdate
```

V3 不自行实现上传协议，也不替换原版认证、事务密码、上传 URL、HTTP/HPP、Complete 或 Rollback。

---

## 2. 安装前要求

建议至少满足：

1. Pokémon Bank v1.5，Title ID：`00040000000C9B00`；
2. Luma3DS 已开启 game patching；
3. 能正常使用原版 Pokémon Bank 联动流程；
4. SD 卡可写；
5. 测试前已经另外备份重要存档/Bank 数据；
6. 第一轮官方保存测试不要直接使用大批量 30 / 300 / 3000 Pokémon。

V3 **不需要旧 Preview 的 RomFS 覆盖**。

如果以前安装过 Route A Offline/Scheme B，请先移走：

```text
SD:/luma/titles/00040000000C9B00/romfs/
```

避免旧版菜单文案或资源替换继续生效。

---

## 3. 安装补丁

最终只需要：

```text
SD:/luma/titles/00040000000C9B00/
└── code.ips
```

不要再额外放 V1/V2/Scheme B 的 `romfs`。

当前 V3 Preview 的 `code.ips`：

```text
size: 1635 bytes
SHA-256:
9D17E1126316878497E07D1D1234860227B031EB26A9B9100C82B24806E3BDEE
```

安装后完全关闭并重新启动 Pokémon Bank，确保旧进程没有继续驻留。

---

## 4. `bulk_import.bin` 放哪里

固定路径：

```text
SD:/3ds/Bank/bulk_import.bin
```

V3 接受两种长度：

```text
0xACA48  = PKHeX Bank7 兼容视图
0xBB518  = Pokémon Bank v1.5 current image
```

并要求文件 header 满足：

```text
version  = 2
boxCount = 100
```

### 4.1 V3 实际会从 bulk 读取什么

只把 bulk 当作“100 Box 内容输入源”。

使用：

```text
主 100 Box 的 30 × 0xE8 Pokémon records
每个 Box 的 0x26 Box metadata
```

不会把 bulk 中这些 current-only metadata 当权威数据：

```text
per-slot tag
source software
timestamp
source summary
NKZT
counters
tail
Transfer Box
server/account/session-like fields
```

这些仍以刚从服务器下载的 fresh BankObject 为基底，由 runtime merge 规则保留或生成。

---

## 5. `bulk_import.bin` 永远只读

这是 V3 的硬性契约。

补丁只会：

```text
OPEN_READ
```

不会：

```text
删除 bulk_import.bin
重命名 bulk_import.bin
覆盖 bulk_import.bin
写回 metadata
保存成功后归档
```

因此同一个 `bulk_import.bin` 可以一直留在 SD 卡。

但要注意：**只要它还叫 `bulk_import.bin`，每次满足普通 Bank 下载 gate 时都会再次尝试 Apply。**

所以在做“服务器是否真的保存成功”的 round-trip 验证时，必须临时把它移走/改名，避免把“重新 Apply”误判成“服务器已持久化”。

---

## 6. 正常运行时会发生什么

普通游戏联动时：

```text
原版下载 fresh BankObject
        ↓
V3 state gate 命中
        ↓
生成完整 fresh backup
        ↓
查询当前联动游戏 metadata context
        ↓
读取 bulk_import.bin（只读）
        ↓
逐槽比较 server vs bulk
        ↓
merge Pokémon + stock-derived metadata
        ↓
进入原版 Bank UI
```

如果没有 `bulk_import.bin`，或 bulk 无效，V3 不会强行报错替换，而是继续原版流程。

---

## 7. 自动备份

Apply 之前，V3 会先备份刚从服务器下载、尚未被 bulk 修改的完整 Bank body：

```text
SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

大小：

```text
0xBB518
```

这个文件代表本次联动的 fresh server 基线。

顺序严格是：

```text
fresh server Bank
→ backup 成功
→ 才允许 Apply bulk
```

如果 backup 写入失败，则本次不 Apply bulk。

如果 bulk 已经开始读/改 runtime 后发生部分读取失败，V3 会尝试从刚创建的 backup 恢复完整 `0xBB518` runtime Bank，再回到原版流程。

---

## 8. Slot merge 规则

对 3000 个主 Box slot 分别比较 fresh server record 与 bulk record。

### 8.1 完全相同

```text
Pokémon 保持
Tag 保持 server 值
Source 保持 server 值
Timestamp 保持 server 值
```

不会因为每次登录都带着同一份 bulk 就反复刷新 metadata。

### 8.2 occupied → empty

```text
Pokémon record 清空
原 tag/source/timestamp 保留
```

依据是真实 Bank 样本里存在大量“当前为空，但历史 metadata 仍非 0”的 slot。

### 8.3 empty → occupied

```text
写入 bulk Pokémon
Tag       = 当前联动游戏 profile 对应格式
Source    = 当前联动软件的 stock sourceSoftware
Timestamp = Bank 原版时间链得到的当前 timestamp
```

### 8.4 occupied → occupied changed

视作 replace/deposit：

```text
写入新 Pokémon
刷新 tag/source/timestamp
```

---

## 9. 第一次测试：H0（不带 bulk）

第一步不要直接测试上传。

把：

```text
SD:/3ds/Bank/bulk_import.bin
```

临时改名，例如：

```text
bulk_import.off
```

然后：

```text
启动 Bank
→ 正常登录
→ 检查 X/Y/ORAS/SM/USUM 游戏列表
→ 选择一个游戏正常联动
→ 能正常进入 Bank UI
```

H0 目标只验证：

```text
原版游戏识别正常
正常联网路径正常
单 Hook 不导致 crash
```

如果 H0 都失败，不要继续做 bulk/save 测试。

---

## 10. 第二步：H1-preview（带 bulk，但先不保存）

把文件恢复为：

```text
SD:/3ds/Bank/bulk_import.bin
```

建议 bulk 里只做非常小的可识别变化。

然后正常：

```text
登录
→ 选择游戏
→ 下载 Bank
→ 进入 Bank UI
```

确认两件事：

1. `SD:/3ds/Bank/` 出现新的 `bankdata_YYYYMMDD_HHMMSS.bin`；
2. Bank 上屏显示的是 merge 后的 bulk 目标内容。

这一阶段只验证：

```text
fresh download
→ backup
→ Apply
→ UI preview
```

**先退出，不做大批量官方保存。**

---

## 11. 第三步：H1-round-trip（只用 1 只 Pokémon）

准备一个只改变 1 个 slot 的 bulk：

```text
例如 Box 1 Slot 1：
server empty → bulk 1 Pokémon
```

正常进入 Bank，确认该 Pokémon 出现后，使用**原版 Bank 保存操作**保存并正常退出。

保存完成以后，最关键的一步：

```text
bulk_import.bin
→ 临时改名 bulk_import.off
```

然后重新：

```text
启动 Bank
→ 正常联网
→ 重新下载官方 Bank
→ 不允许 V3 再 Apply bulk
→ 查看 Box 1 Slot 1
```

只有在 bulk 已移走的情况下，重新下载仍能看到该 Pokémon，才证明：

```text
runtime merge
→ stock serialize
→ PrepareUpdate
→ HPP upload
→ CompleteUpdate
→ server persistence
→ redownload
```

真正闭环。

不要在 `bulk_import.bin` 仍存在时用肉眼看到 Pokémon 就判断服务器保存成功，因为那可能只是再次 Apply。

---

## 12. 放大测试规模

只有 H1-round-trip 成功后再逐步扩大：

```text
1 Pokémon
→ 30 Pokémon / 1 Box
→ 300 Pokémon / 10 Box
→ 3000 slots / 100 Box
```

每一级都建议保留：

```text
本次 fresh backup
测试用 bulk_import.bin 的副本
保存后的 server redownload
测试时间/联动游戏/结果记录
```

便于之后做结构化 diff。

---

## 13. HOME 使用

V3 的 state gate 明确排除 special path，设计上不会在 HOME/full-download 路径重复 Apply bulk。

但第一次验证建议仍采用最清晰的流程：

```text
完成 1 Pokémon server round-trip
→ 临时移走 bulk_import.bin
→ 正常重新进入 Bank
→ 正常走 HOME transfer
```

这样能把“Bulk Apply”和“HOME transfer”两条路径完全隔离，便于定位问题。

---

## 14. 如果没有 bulk 或 bulk 无效

以下情况都不会强制替换 server Bank：

```text
文件不存在
文件长度不是 0xACA48 / 0xBB518
version != 2
boxCount != 100
metadata context 获取失败
fresh backup 创建失败
```

V3 的策略是尽量 fail closed：无法证明输入/运行时上下文符合预期时，不做 bulk merge，让原版 Bank 继续运行。

---

## 15. 常见问题

### Q1：还需要 `bankdata.bin` 吗？

Official-only V3 的正常联网路径不依赖 Route A Offline 的本地 `bankdata.bin` 作为运行时基底。

基底是**本次刚从官方服务器下载的 fresh BankObject**。

自动生成的 `bankdata_YYYYMMDD_HHMMSS.bin` 是备份证据，不是 Offline Mode 的启动数据源。

### Q2：还需要 `romfs` 吗？

不需要。

V3 不再做 Offline/Download 菜单资源替换。建议删除旧：

```text
SD:/luma/titles/00040000000C9B00/romfs/
```

### Q3：PKHeX 保存的 `0xACA48` 可以直接用吗？

可以，只要 header 仍是 Bank7：

```text
version = 2
boxCount = 100
```

直接改名：

```text
bulk_import.bin
```

放入 `/3ds/Bank/`。

### Q4：完整 `0xBB518` 可以用吗？

可以，但 V3 仍只把它当 data-only bulk。后半段 tag/source/time/NKZT 等不会整块覆盖服务器 runtime。

### Q5：保存成功后补丁会改 bulk 吗？

不会。`bulk_import.bin` 永远只读。

### Q6：为什么服务器验证时必须移走 bulk？

因为不移走时，下一次登录会再次 Apply，无法区分“服务器持久化”与“本地再次覆盖”。

---

## 16. 回退/卸载

完全关闭 Pokémon Bank 后删除或改名：

```text
SD:/luma/titles/00040000000C9B00/code.ips
```

即可回到原版 `.code` 行为。

`/3ds/Bank/bulk_import.bin` 和自动 backup 文件不属于 Luma patch 本体，可自行保留/移动。

---

## 17. 当前验证状态

### 已静态/CI 验证

```text
host merge/state contract
ARMv6K Thumb -Werror
payload size budget
禁止 __aeabi division helper
禁止旧 OfficialBulk_CommandBuffer relocation
armips / IPS replay
mapped .data byte-for-byte preserve
```

### 已实机确认的历史问题

```text
V1 mapped .data 污染会破坏游戏识别
V2 游戏列表恢复
V2 Thumb→ARM relocation 会造成 PC=0x00313BB0 undefined instruction
```

### V3 仍需实机继续确认

```text
H0：正常联动不崩
H1-preview：backup + bulk UI
H1-round-trip：1 Pokémon Save → bulk off → redownload
之后 30 / 300 / 3000
```

---

## 18. 相关文档

- `official-bank-bulk-sync-principles-v3.zh-cn.md`：完整原理解析；
- `official-bank-bulk-sync-technical-v3.zh-cn.md`：V2 crash 与 V3 interworking 修复；
- `official-bank-bulk-sync-design.zh-cn.md`：只读 bulk / original save transaction 等设计契约；
- `saveboxes-transaction-analysis.zh-cn.md`：原版 PrepareUpdate / HPP / CompleteUpdate / Rollback 事务逆向；
- `official-bank-bulk-sync-build-release-guide-v3.zh-cn.md`：源码编译、静态验证、打包和 GitHub Release 流程。
