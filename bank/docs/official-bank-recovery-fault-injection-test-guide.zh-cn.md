# Pokémon Bank v1.5 Recovery A/B 实机故障注入测试指南

> 仅用于 `feature/official-bank-recovery-a-fault-injection` 与 `feature/official-bank-recovery-b-fault-injection` 测试分支。
>
> 测试会**故意把官方 Bank 保存事务停在未完成状态**。请先备份游戏存档，并使用可承受回滚/重做的测试 Pokémon 与 `bulk_import.bin`。不要在有重要未备份 Bank 变更时执行。

## 1. 测试目标

不再依赖“手动断网时间碰巧正确”，而是在三个已静态确认的事务边界把 Bank 固定冻结：

| fault point | VA | 命中时已经发生 | 尚未发生 |
|---|---:|---|---|
| `post-stage` | `0x002B1E18` | Prepare/Stage 已成功，服务器有机会存在 pending transaction；pre-WAL 已持久化 | 游戏 recovery record / game save |
| `post-game-save` | `0x002B1F4C` | 游戏 recovery record 已写入，game save callback 已明确成功 | case5 Bank-local recovery rewrite |
| `pre-complete` | `0x002B20A0` | game save 与 Bank-local recovery 都已经完成 | `CompleteUpdateBankObject` 调用 |

每个测试构建仅把目标点原始 ARM 指令替换为：

```text
FE FF FF EA    ; ARM: B .
```

即确定性自循环。没有新增网络请求、文件写入、线程、异常或随机延时。

## 2. 为什么选择这三个点

### 2.1 `post-stage @ 0x002B1E18`

stock：

```asm
LDR R0,[R4,#8]
```

这是 state7 case3 入口。进入这里意味着 Stage callback 已经把事务推进到“可以开始写游戏 recovery record”的阶段。

预期：

```text
A -> Rollback
B -> Rollback
```

### 2.2 `post-game-save @ 0x002B1F4C`

stock：

```asm
LDR R0,[R4,#8]
```

只有 game-save callback 明确返回成功，状态机才会进入该 case5 入口。

因此这里可以验证最关键的 A/B 差异：

```text
A -> Rollback
B -> Commit
```

B 的 Commit 依据是：同一个 transaction 的游戏 recovery record 已经 durable 为 `status=2`。

### 2.3 `pre-complete @ 0x002B20A0`

stock：

```asm
LDR R0,[R4,#0x40]
```

后续紧接：

```asm
LDR R1,[R4,#0x28]
MOV R2,#0
BL  0x001D5D74    ; CompleteUpdateBankObject
```

因此冻结时 Complete 还没有发出，但 local/game recovery 都应已经持久化。

预期：

```text
A -> Rollback
B -> Commit
```

## 3. 生成三套 fault IPS

前提：

```text
bank/rom/exefs/00040000000C9B00.dec.code
```

必须是已验证 Bank v1.5 stock `.code`：

```text
size    = 0x2AC000
SHA-256 = 2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

在对应 fault-injection 分支的 `bank/src` 下：

```bash
make fault-matrix
```

工具会先正常生成并验证 production A/B patch，然后生成：

```text
release/fault-injection-A/00040000000C9B00/
或
release/fault-injection-B/00040000000C9B00/

code-fi-post-stage.ips
code-fi-post-stage.dec.code
code-fi-post-stage.json

code-fi-post-game-save.ips
code-fi-post-game-save.dec.code
code-fi-post-game-save.json

code-fi-pre-complete.ips
code-fi-pre-complete.dec.code
code-fi-pre-complete.json
```

JSON manifest 会记录：

```text
variant
fault point
virtual address
stock instruction
B . instruction
expected recovery
stock SHA-256
production-patched SHA-256
fault .code SHA-256
fault IPS SHA-256
```

工具对以下情况全部 fail-closed：

- stock SHA 不匹配；
- `.code` size 不匹配；
- stock 目标地址不是已验证原字节；
- production A/B 已经修改了 fault target；
- 最终 IPS replay 不能精确得到 fault `.code`。

## 4. 每轮实机测试前的清洁起点

每一个 fault point 都应从独立的 clean transaction 开始，不要连续叠加。

建议顺序：

1. 使用**正常 production A/B IPS**启动 Bank 一次；
2. 确认没有未完成事务提示、Trainer mismatch 或 recovery UI；
3. 正常退出；
4. 备份当前联动游戏 `main`；
5. 记录该 `main` 的 SHA-256；
6. 准备一份容易识别、但不重要的 `bulk_import.bin`；
7. 记录 Bulk 前服务器 Bank 状态/自动 snapshot；
8. 关机后安装本轮 fault IPS。

测试用 Bulk 最好每轮有明显不同，例如只修改一个固定 Bank slot，并记录该 Pokémon 的 species/PID/EC 或其他唯一标记，便于区分“Commit”和“Rollback”。

## 5. 单轮测试操作

以任一 fault IPS 为例：

### 阶段 A：制造中断

1. 把选定文件重命名/部署为 Luma 对 Bank 使用的 `code.ips`；
2. 确认启用 `Enable game patching`；
3. 启动 Pokémon Bank；
4. 选择测试游戏；
5. 等 Official Bulk Sync 正常载入并应用 `bulk_import.bin`；
6. 执行 Bank 保存；
7. 等待画面/程序出现稳定冻结；
8. 冻结后不要继续等待网络超时——该点是 CPU 自循环，不会自行恢复；
9. 长按电源关机。

### 阶段 B：恢复测试

**重新开机前/重新启动 Bank 前必须：**

1. 删除 fault `code.ips`；
2. 换回对应的正常 production A 或 production B `code.ips`；
3. 不要 JKSM restore；
4. 不要打开游戏重新保存；
5. 不要修改 Pokémon；
6. 不要换另一份卡带/数字版 save；
7. 继续使用刚才被冻结时的同一份游戏 `main`。

然后：

1. 启动 Bank；
2. 登录官方服务器；
3. 选择同一游戏；
4. 记录是否出现自动 recovery；
5. 记录是否进入正常 Bank Box、Trainer mismatch、网络错误或其他 UI；
6. 若成功恢复，重新下载服务器 BankObject 后核对测试 slot；
7. 保存 recovery 后得到的 Bank snapshot；
8. 再正常退出一次，确认后续再次进入不再出现 pending/mismatch。

## 6. 预期矩阵

| fault point | Recovery A | Recovery B | 服务器最终期望 |
|---|---|---|---|
| `post-stage` | Rollback | Rollback | Bulk 变更不应持久化 |
| `post-game-save` | Rollback | Commit | A 不持久化；B 应持久化 |
| `pre-complete` | Rollback | Commit | A 不持久化；B 应持久化 |

### A 的判定

A 的设计目标是“异常退出一律撤销本轮 Bulk transaction”。

因此三个测试点若都能：

```text
下一次启动
-> stock recovery
-> Rollback
-> 正常进入 Bank
-> server Bank 保持本轮保存前版本
```

才符合 A 语义。

### B 的判定

B 的核心边界是“game save 是否已经 durable 成功”：

```text
post-stage
  game recovery 尚未保存
  -> Rollback

post-game-save
  game recovery status=2 已 durable
  -> Commit

pre-complete
  game + local recovery 均已 durable
  -> Commit
```

## 7. 每轮必须保存的证据

建议建目录：

```text
fault-tests/
  A-post-stage/
  A-post-game-save/
  A-pre-complete/
  B-post-stage/
  B-post-game-save/
  B-pre-complete/
```

每轮保存：

```text
fault manifest JSON
使用的 fault code.ips SHA-256
使用的 production recovery code.ips SHA-256
freeze 前 game main SHA-256
freeze 后、recovery 前 game main SHA-256（若方便导出）
recovery 后 game main SHA-256（若方便导出）
Bulk 前 Bank snapshot
recovery 后 Bank snapshot
UI 照片/视频
测试 slot 的 before/after 标识
最终结果：ROLLBACK / COMMIT / MISMATCH / OTHER
```

最重要的是：**freeze 后到 recovery 启动前不要恢复旧存档。** 这次实验就是验证“同一份、未 restore、未修改的 save”能否由 A/B 正确处理。

## 8. 失败如何解释

### `post-stage` 仍 Trainer mismatch

优先说明：

- pre-WAL 没有真正 durable；或
- server pending transaction 与 WAL exact fields 不一致；或
- state18 没有命中预期恢复路径。

应优先保留现场，不要再次保存。

### B `post-game-save` / `pre-complete` 发生 Rollback

优先检查：

- game recovery record 是否真的为当前 transaction；
- game `status=2` 是否已 durable；
- local private WAL exact-match 是否失败；
- state18 的 `+0x88` evidence path 是否按预期从 2 转为 1。

### 出现 Commit 但 Bulk 数据没上服务器

说明需要区分：

- Complete 的 transaction 是否对应当前已上传 BankObject；
- Stage/HPP 上传是否真正完成；
- UI 所谓“进入 case3”与服务端对象可提交状态是否完全一致。

这会是下一轮抓 transaction param / HPP callback 的重点。

## 9. 测试顺序建议

先做风险最低、信息量最高的顺序：

```text
B post-stage
A post-stage
B post-game-save
A post-game-save
B pre-complete
A pre-complete
```

先验证两条线都能从最早 pending 窗口安全 Rollback，再测试 A/B 的分歧点。

不要一开始就连续做六轮；每轮确认 server/game 已重新进入 clean 状态后再进入下一轮。
