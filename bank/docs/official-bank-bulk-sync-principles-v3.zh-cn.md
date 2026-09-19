# Pokémon Bank v1.5 Official Bulk Sync V3 原理解析与端到端技术说明

> 分支：`feature/official-bank-bulk-sync`
>
> 本文描述 V3 的完整工作原理：为什么只 Hook `BankDataSyncState_Update`、如何判定“普通游戏联动 Bank 下载刚完成”、如何取得 fresh `BankObject`、为什么先备份再 Apply、`bulk_import.bin` 的只读语义、slot-aware metadata writer、原版 Save/Upload 事务如何保持不变，以及 V1/V2 两次实机故障如何反推当前安全边界。
>
> 结论状态分为三类：**已静态确认**、**已实机确认**、**仍待官方服务器 round-trip 验证**。不要把三者混为一谈。

---

## 1. 项目目标

目标不是重新实现 Pokémon Bank 服务端协议，也不是做一个独立 Online Mode，而是在原版 Bank 正常联网流程中插入一个极小的 runtime 数据变换：

```text
原版登录
→ 原版选择游戏
→ 原版下载官方 BankObject
→ [V3：备份 fresh BankObject]
→ [V3：把 bulk_import 的主 100 Box 合并到 runtime BankObject]
→ 原版 Bank UI
→ 用户人工检查
→ 原版保存
→ 原版 PrepareUpdate / HPP / CompleteUpdate
→ 官方服务器持久化
```

补丁不接管：

```text
账号认证
NEX 会话
transactionPassword
DataStore transaction version
上传 URL
HTTP headers
multipart form fields
证书
Complete / Rollback
HOME transfer
```

核心思想是：**只修改即将被原版序列化保存的 runtime BankObject，不重新发明官方上传协议。**

---

## 2. 为什么必须以 fresh server BankObject 为基底

`bulk_import.bin` 只代表用户想要的主 Box 内容，不应被视为完整账号 Bank 镜像。

真正的官方 BankObject 除了 100 Box Pokémon 之外还包含：

```text
Header / version / identity-like fields
Transfer Box
per-slot format tag
source software
per-slot timestamp
source summaries
NKZT aggregate block
counters
reserved/tail
以及和当前 server object 一致的其它 current-format 状态
```

因此 V3 使用：

```text
fresh server BankObject
    + bulk 的主 100 Box payload
    + stock-derived metadata
```

而不是：

```text
bulk_import.bin 整文件覆盖 runtime BankObject
```

这样可以最大限度保留服务器刚刚下发的 current object 状态。

---

## 3. Bank v1.5 文件与 runtime object 基线

目标应用：

```text
Title ID: 00040000000C9B00
Pokémon Bank: v1.5
Image base: 0x00100000
stock .code SHA-256:
2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

完整 current Bank body：

```text
0xBB518 bytes
```

PKHeX Bank7 兼容视图：

```text
0xACA48 bytes
```

主 100 Box 区间：

```text
0x00017C .. 0x0AAF14   end-exclusive
```

Box 布局：

```text
30 × 0xE8 Pokémon record = 0x1B30
Box metadata              = 0x26
Box stride                = 0x1B56
Box count                 = 100
```

slot 计算：

```text
index = box * 30 + slot
pkm   = 0x17C + box * 0x1B56 + slot * 0xE8
```

parallel metadata：

```text
tag       = 0xACA44 + index
source    = 0xB4AA0 + index
timestamp = 0xB5658 + index * 8
```

runtime `BankObject` 本身还有 8-byte object header，序列化 body 对应：

```text
body = object + 8
```

当前 vtable：

```text
0x003626FC
```

---

## 4. V3 只使用一个原版 Hook

唯一原版执行点：

```text
BankDataSyncState_Update = 0x002AF460
```

原位置前 4 bytes 被替换成跳转：

```asm
b OfficialBulk_BankDataSyncDispatch
```

V3 没有再 Hook：

```text
BankRemote_DownloadSuccessCallback
BankSaveState_Update
BankSave_SerializeAndStage
BankRemote_StageFileUpdate
Commit / Rollback
HOME state
```

这样做的原因有两个：

1. 原版 `BankDataSyncState` 自己已经保存足够的下载完成状态，不需要额外 pending flag；
2. Hook 越少，对原版联网、游戏识别、保存状态机的干扰越小。

---

## 5. 原版 state 自带“下载完成”判定

V3 不维护自定义全局状态，而直接读取当前 `BankDataSyncState`：

```text
state + 0x10 : substate
state + 0x40 : callbackStatus
state + 0x41 : specialFlag
```

当前 gate：

```c
substate == 2
&& callbackStatus == 1
&& specialFlag == 0
```

即：

```c
OfficialBulk_ShouldProcessState(substate, callbackStatus, specialFlag)
```

只有这三个条件同时成立时才进入 backup/apply。

这一设计的作用是把“普通游戏联动的 Bank 下载完成”从其它远端路径中隔离出来。

尤其：

```text
specialFlag != 0
→ 不处理
```

用于排除特殊 full-download 路径，包括不应重复 Apply 的 HOME 相关路径。

---

## 6. ARM dispatcher 与 ARM/Thumb interworking

V3 payload 放在真正的 RX text tail：

```text
TextActualEnd = 0x00313910
TextMappedEnd = 0x00314000
```

dispatcher 运行在 ARM 状态：

```asm
OfficialBulk_BankDataSyncDispatch:
    push {r4-r6,lr}
    mov  r4,r0

    mrc  p15,0,r1,c13,c0,3
    add  r1,r1,#0x80

    ldr  r12,=OfficialBulkSync_Process+1
    blx  r12

    mov  r0,r4
    b    BankDataSyncState_Update + 4
```

参数：

```text
r0 = BankDataSyncState *
r1 = thread command buffer = TLS + 0x80
```

`OfficialBulkSync_Process+1` 的 bit0 用于 ARM→Thumb interworking。

### 为什么 command buffer 在 ARM dispatcher 里取得

raw FS IPC 需要线程 command buffer。3DS 用户态通常通过 CP15 TLS：

```asm
mrc p15,0,rX,c13,c0,3
add rX,rX,#0x80
```

V2 曾让 Thumb C 通过外部 `R_ARM_THM_CALL` 调 ARM helper 获取 command buffer，最终在 armips `.importobj` relocation 上触发了 2-byte 偏差。

V3 直接在 ARM dispatcher 中执行 MRC，再把结果作为普通参数传给 Thumb C，完全移除这类跨 ISA external relocation。

---

## 7. V1/V2 两次故障为何决定了当前安全边界

### V1：错误使用 mapped `.data` 作为 code cave

旧实现把：

```text
0x003ABA90 .. 0x003ABFFC
```

当成“文件里是 0，所以可执行”的洞。

但该区间位于：

```text
DataMappedStart = 0x0036A000
DataMappedEnd   = 0x003AC000
```

属于活跃 mapped `.data` / 全局状态区，并被原版大量 literal/reference 使用。

实机表现：

```text
Sun/Moon/Ultra Sun/Ultra Moon 存档不再显示
prefetch abort
```

因此得到硬规则：

> 文件中全零不等于可作为 code cave；必须同时验证映射权限、段类型和原版引用。

当前 verifier 强制：

```text
0x0036A000 .. 0x003AC000
```

与 stock binary **逐字节完全一致**。

### V2：Thumb→ARM external relocation 偏移 2 bytes

V2 crash：

```text
Exception: undefined instruction
PC: 0x00313BB0
CPSR: Thumb
```

错误机器码：

```text
FF F7 BD EE
```

标准 linker 对同样 source/target 的正确 BLX：

```text
FF F7 BE EE
```

等价于 armips 把目标从：

```text
0x0031392C
```

错成：

```text
0x0031392A
```

因此 V3 的第二条硬规则：

> imported Thumb object 不允许通过外部 `R_ARM_THM_CALL` 调用 armips 区里的 ARM helper。

CI 会拒绝 `OfficialBulk_CommandBuffer` undefined symbol 或 relocation。

---

## 8. Runtime BankObject 获取

`OfficialBulkSync_Process(state, commandBuffer)`：

```c
flow   = *(u8 **)(state + 8);
object = flow ? *(u8 **)(flow + 0xCC) : 0;
body   = object + 8;
```

进入任何写操作前检查：

```text
state != NULL
commandBuffer != NULL
state gate == true
object != NULL
*(u32 *)object == 0x003626FC
u16(body + 0x15C) == 2
u16(body + 0x15E) == 100
```

任何检查失败都直接返回，并继续原版状态机。

---

## 9. 为什么先备份 fresh BankObject

补丁的第一项副作用不是 Apply，而是备份：

```text
fresh server runtime BankObject
→ writeSnapshot
→ 成功后才允许 bulk Apply
```

备份路径：

```text
/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

完整长度：

```text
0xBB518
```

这样备份代表“本次官方刚下载、尚未被 bulk 改动”的基线。

### 备份写入

```text
OpenFileDirectly
→ OPEN_READ | OPEN_WRITE | OPEN_CREATE
→ raw FSFILE SetSize IPC = 0xBB518
→ FSFILE_Write offset 0, WRITE_FLUSH
→ FSFILE_Close
```

只有以下全部满足才算成功：

```text
open/result == 0
setSize == 0
write == 0
written == 0xBB518
close == 0
```

备份失败时不 Apply bulk。

---

## 10. `bulk_import.bin` 的只读契约

路径：

```text
/3ds/Bank/bulk_import.bin
```

支持长度：

```text
0xACA48  PKHeX Bank7 view
0xBB518  current Bank v1.5 image
```

必须满足 header：

```text
version  = 2
boxCount = 100
```

补丁只以：

```text
OPEN_READ
```

打开它。

永远不会：

```text
删除
重命名
覆盖
写回 metadata
保存成功后归档
```

因此 `bulk_import.bin` 是 immutable input。

---

## 11. 为什么 bulk 只负责 Pokémon/Box 数据

即使输入长度是完整 `0xBB518`，V3 也不信任 bulk 中 current-only metadata。

bulk 仅提供：

```text
主 100 Box 里的 30×0xE8 Pokémon
每 Box 0x26 metadata
```

不会直接复制：

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

这是“fresh server base + data-only bulk overlay”的核心。

---

## 12. Slot-aware merge 原理

每槽比较：

```text
fresh server record
vs
bulk record
```

### 情况 A：完全相同

```text
Pokémon 不写
Tag 保持 server
Source 保持 server
Timestamp 保持 server
```

这样即使用户长期保留同一份 bulk，也不会每次登录都刷新 metadata。

### 情况 B：occupied → empty

bulk record 为全 0：

```text
Pokémon record 清零
Tag 保留历史值
Source 保留历史值
Timestamp 保留历史值
```

这是根据真实 Bank 样本推导：很多历史清空槽仍保留 nonzero metadata。

### 情况 C：empty → occupied

```text
复制 bulk Pokémon
Tag = 当前 game profile 对应格式
Source = 当前联动软件
Timestamp = stock runtime 当前时间
```

### 情况 D：occupied → occupied changed

视作一次新的 replace/deposit：

```text
复制新 Pokémon
刷新 Tag
刷新 Source
刷新 Timestamp
```

---

## 13. format tag 的生成

当前映射：

```text
profile 1..4 → tag 0
profile 5..8 → tag 1
其它         → unsupported
```

实现：

```c
OfficialBulk_FormatTagForProfile(profile)
```

当前语义：

```text
Gen6-linked profile → Bank format 0
Gen7-linked profile → Bank format 1
```

注意：该映射已通过 host contract test，但“服务器接受后是否完全等价于 stock 每一种 deposit 场景”仍需要官方 round-trip 继续验证。

---

## 14. source software 的生成

V3 不从 Pokémon origin game 推断 source。

它从当前 active game model 取得 stock source object：

```text
GAME_REGISTRY_SLOT = 0x003AB90C
GameModelActive    = 0x00233A6C
```

流程：

```text
registry = *GAME_REGISTRY_SLOT
model = GameModelActive(*(registry + 0x1C))
profile = model[8]
```

source object：

```text
profile >= 5 → model + 0x74304
profile <  5 → model + 0x129AC
```

随后调用该对象 vtable `+0x0C`：

```text
sourceSoftware = vtable[3](sourceObject)
```

这样 metadata 使用“当前联动软件”而不是 Pokémon 原始捕获版本。

这与真实样本观察一致：Bank 中 source software 更像“最后一次写入 Bank 时的联动软件”。

---

## 15. timestamp 的生成

V3 复用 stock helper：

```text
0x00234648  TimeContainerInit
0x001D3BF4  TimeQuery
0x001F2BD4  TimePack
```

流程：

```text
TimeContainerInit(stamp)
→ TimeQuery(*(root + 0x138), stamp)
→ TimePack(stamp)
→ u64 timestamp
```

这样避免自行实现 Nintendo/Bank 时间编码。

前期样本表明该值与 Nintendo 2000 epoch 秒高度一致，但 V3 运行时仍以 stock helper 输出为准。

---

## 16. Box metadata

每个 Box 末尾：

```text
0x26 bytes
```

由 bulk 直接复制。

其中包含 Box 名称/index 等主 Box 范畴的数据，因此属于用户编辑目标的一部分。

这和 per-slot current metadata 是两个层次：

```text
Box metadata     ← bulk
slot tag/source/time ← runtime writer
```

---

## 17. 失败处理与 runtime 恢复

`applyBulkFile()` 返回：

```text
 1 = apply 完成
 0 = 没有可用 bulk / header 不支持
-1 = 已经可能部分修改 runtime，随后发生 I/O/merge 失败
```

如果返回 `-1`：

```text
restoreSnapshot(backupPath, runtime body)
```

把刚才完整写出的 fresh backup 重新读回 `0xBB518` runtime body。

因此中途读取 bulk 失败不会故意留下半套 Box 数据继续给原版 UI。

---

## 18. 为什么不 Hook 保存链

用户在 Bank UI 按保存后，V3 不再介入。

原版路径：

```text
0x002B1CF8  BankSaveState_Update
→ 0x002B2320 BankSave_SerializeAndStage
→ 序列化 0xBB518
→ 0x002A2504 BankRemote_StageFileUpdate
→ RMC 52 PrepareUpdateBankObject
→ HPP/HTTPS 上传
→ RMC 53 CompleteUpdateBankObject
→ 0x001D5D74 Commit
```

失败：

```text
0x001D5C28 Rollback
```

也就是说，V3 只改变“原版保存前 runtime object 的内容”。

事务对象：

```text
dataId
curVersion
updateVersion
transactionPassword
size
```

仍由当前官方 session 原生生成和维护。

---

## 19. 为什么这种设计比“自己上传一个 Bank 文件”更稳

如果补丁自己实现上传，需要正确复刻：

```text
NEX auth context
slot/dataId
curVersion/updateVersion
transactionPassword
PrepareUpdate
server-provided URL
headers/form fields
redirect/retry
Complete/Rollback
冲突恢复
```

而 runtime-overlay 设计把这些全部留给 stock Bank。

补丁只解决自己最明确的领域：

```text
fresh BankObject
+ 用户 Box 数据
→ candidate runtime BankObject
```

这样协议风险和账号/session 风险显著更小。

---

## 20. HOME 为什么不应再次 Apply

最终理想流程：

```text
普通游戏联动
→ fresh Bank download
→ bulk Apply
→ 用户保存上传

稍后 HOME transfer
→ 服务器下载已经保存的 Bank
→ 不 Apply bulk
→ 正常转 HOME
```

如果 HOME full-download 也 Apply bulk，会把“上传阶段的输入”再次注入 transfer path，导致语义混乱。

因此 V3 用原生 state gate 的 `specialFlag==0` 限制普通路径。

---

## 21. 代码布局与 patch 白名单

允许修改范围：

```text
0x002AF460 .. 0x002AF464   单 Hook
0x00313910 .. 0x00314000   RX text-tail payload
```

禁止修改：

```text
0x0036A000 .. 0x003AC000   mapped data image
```

当前关键 symbol：

```text
0x00313910  OfficialBulk_BankDataSyncDispatch
0x003139D4  OfficialBulkSync_Process
```

V3 当前 `code.ips`：

```text
size: 1635 bytes
SHA-256:
9D17E1126316878497E07D1D1234860227B031EB26A9B9100C82B24806E3BDEE
```

---

## 22. 构建链

生产对象：

```text
official_bulk_sync_prod.c
  includes:
  official_bulk_sync_core.c
  official_bulk_sync.c
```

编译目标：

```text
ARMv6K Thumb
-Os
-ffreestanding
-fno-builtin
-fno-stack-protector
-fno-unwind-tables
-Wall -Wextra -Werror
```

GitHub CI 验证：

```text
host merge/state test
ARMv6K Thumb -Werror compile
拒绝 __aeabi_* division helper
拒绝 OfficialBulk_CommandBuffer symbol
拒绝 OfficialBulk_CommandBuffer relocation
text payload size budget
上传 production ARM object artifact
```

本地使用 CI object + stock `.code`：

```text
armips
→ patched .code
→ flips 生成 IPS
→ verify_official_bulk_sync.py
```

verifier 会检查：

```text
stock SHA-256
只修改白名单地址
text cave 在 stock 中确实为 0
mapped .data 完全一致
关键 symbol 地址
禁止 V2 helper symbol
IPS replay == patched .code
```

---

## 23. 当前已经获得的实机证据

### 已确认

V1 问题复现：

```text
mapped .data 被覆盖
→ Sun/Moon/USUM 游戏识别异常
```

V2 修复后：

```text
Sun/Moon/USUM 游戏重新显示
```

V2 联动 crash：

```text
undefined instruction
PC 0x00313BB0
```

并已精确闭合到错误 Thumb→ARM BLX relocation。

### V3 当前静态/CI 已确认

```text
没有 .data payload
没有 pending scratch
没有 OfficialBulk_CommandBuffer helper relocation
只 Hook 0x002AF460
生产对象编译通过
IPS replay verifier 通过
```

### 仍待实机确认

```text
V3 H0：无 bulk 正常联动不 crash
V3 H1-preview：fresh backup + bulk UI 显示
V3 H1-round-trip：1 Pokémon 保存后重新下载仍存在
```

---

## 24. 分级验证协议

### H0：纯原版行为隔离

暂时把：

```text
bulk_import.bin → bulk_import.off
```

验证：

```text
游戏列表正常
Gen6/Gen7 任意游戏可联动
不会在 BankDataSync 时 crash
```

### H1-preview：只验证 Apply，不保存

恢复 `bulk_import.bin`：

```text
官方正常下载
→ 生成 bankdata_时间.bin
→ Bank UI 看到 bulk 内容
→ 不保存退出
```

检查 backup：

```text
size = 0xBB518
header version = 2
boxCount = 100
```

### H1-round-trip：只改 1 只 Pokémon

```text
服务器 fresh Bank
→ bulk 只改 1 槽
→ UI 检查
→ 原版保存
→ 完全退出
→ 再次联网
→ 重新下载
→ 比较 server-after
```

通过后才扩大：

```text
1 → 30 → 300 → 3000
```

---

## 25. Round-trip 要验证的不只是“能看到 Pokémon”

需要同时比较：

```text
Pokémon record
Box metadata
Tag
Source software
Timestamp
summary/NKZT/counter/tail 是否被 stock save 合理更新
server redownload 后是否稳定
```

尤其要确认：

```text
empty→occupied
occupied→changed
occupied→empty
unchanged
```

四种槽状态在官方保存后的 metadata 行为是否与我们的 writer 假设一致。

---

## 26. 当前明确不做的事情

V3 不做：

```text
伪造 transactionPassword
复用旧 transaction
硬编码 dataId
自己构造官方 upload URL
绕过 NEX auth
修改 HOME 下载
自动按保存
保存成功后修改 bulk_import.bin
```

`bulk_import.bin` 始终只是本地、只读、可重复使用的数据输入。

---

## 27. 维护规则

以后修改 official-only payload 时必须同时满足：

```text
1. 不得把 mapped .data/BSS 当 code cave
2. 不得引入 imported Thumb → external ARM R_ARM_THM_CALL
3. 不得扩大 Hook 到保存事务，除非有独立理由与验证
4. 不得从 bulk 直接覆盖 server/account current-only metadata
5. 不得写回 bulk_import.bin
6. 每次改布局都重新跑 IPS whitelist + replay verifier
7. 每次改 merge 规则都更新 host contract test
```

---

## 28. 相关文档

- `official-bank-bulk-sync-technical-v3.zh-cn.md`：V2 crash 与 V3 ARM/Thumb interworking 修复
- `official-bank-bulk-sync-design.zh-cn.md`：只读 bulk、original-save、HOME 排除等设计契约
- `saveboxes-transaction-analysis.zh-cn.md`：原版 BankObject Prepare/Upload/Complete/Rollback 事务
- `r1-r3-baseline-bankdata-analysis.zh-cn.md`：tag/source/timestamp 样本研究
- `r4-r6-metadata-policy.zh-cn.md`：summary/NKZT/counter/tail 的保留策略
- `bank-v15-legacy-upgrade-analysis.zh-cn.md`：0xACA48 legacy/current 兼容关系

---

## 29. 当前结论

V3 的本质不是“上传一个伪造 Bank 文件”，而是：

```text
官方 session
+ 官方 fresh BankObject
+ 本地只读 Box 数据
+ stock-derived metadata
= 原版 Bank 将要保存的 runtime candidate
```

然后由原版 Bank 自己完成：

```text
Serialize
→ PrepareUpdate
→ HPP upload
→ CompleteUpdate
→ Commit/Rollback
```

这让补丁和服务器协议之间保持最小耦合，也是当前路线最重要的设计原则。
