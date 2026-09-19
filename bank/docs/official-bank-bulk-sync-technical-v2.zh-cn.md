# Pokémon Bank v1.5 Official Bulk Sync 详细技术文档 V2

> 分支：`feature/official-bank-bulk-sync`
>
> 本文档描述 2026-09-19 修正后的 official-only 架构。V1 曾错误地把 mapped `.data` 尾部零区当作 code cave，导致游戏识别全局状态被覆盖；V2 已完全移除该做法。

## 1. 目标

最终用户流程保持原版 Pokémon Bank：

```text
启动 Bank
→ 原版联网登录
→ 原版识别并选择任意兼容游戏
→ state 16 下载 fresh BankObject
→ [补丁：备份 + 只读 bulk merge]
→ 原版 Bank Box UI
→ 用户正常“保存并退出”
→ 原版 PrepareUpdate / HPP / CompleteUpdate
→ 官方服务器
→ 后续正常 Bank → HOME
```

不再需要用户可见的 Offline Mode / Download Mode。

`bulk_import.bin` 是只读 Pokémon/Box 数据源，不携带权威 current metadata，也不会在保存后被删除、改名、覆盖或回写。

---

## 2. V1 故障与根因

### 2.1 用户侧症状

V1 preview 安装后，在进入 bulk merge 之前就出现：

- Pokémon Bank 的联动游戏列表异常；
- 《太阳／月亮》与《究极之日／究极之月》存档不再展示；
- 因为问题发生在 state 16 之前，所以与 `bulk_import.bin` Pokémon 内容无关。

### 2.2 错误假设

V1 使用：

```text
0x003ABA90 .. 0x003ABFFC
```

作为 `official_bulk_sync_core.o` 的代码空间，并把：

```text
0x003ABFFC
```

作为 pending byte。

当时静态 verifier 只验证“原始文件这些 byte 为 0”，误把“文件中为 0”当成“运行时未使用”。

### 2.3 真实 segment 属性

ExHeader / symbol map：

```text
TextActualEnd      0x00313910
TextMappedEnd      0x00314000
RodataMappedStart  0x00314000
DataMappedStart    0x0036A000
DataMappedEnd      0x003AC000
```

因此：

```text
0x003ABA90 .. 0x003ABFFC
```

属于 mapped `.data`，不是 RX `.text`。

### 2.4 原版直接引用证据

扫描原版 `00040000000C9B00.dec.code` 的 literal references 后，在该错误区间找到至少 38 个原版引用，包括：

```text
0x003ABACC
0x003ABBA4
0x003ABC54
0x003ABC7C
0x003ABDC4
0x003ABDF0
0x003ABE20
0x003ABF10
0x003ABF80
0x003ABFA8
0x003ABFCC
0x003ABFD8
```

这证明该区间包含活跃全局数据。

附近还存在已确认的重要全局：

```text
Game registry slot  0x003AB90C
Bank root slot      0x003AB938
```

所以 V1 在程序加载时就会把原版游戏识别/全局状态覆盖成 ARM 指令字节，解释了“SM/USUM 存档列表消失”的症状。

### 2.5 V2 修复原则

V2 强制：

```text
绝不把 .data / BSS / rodata 零字节当作 code cave
```

所有新增可执行代码必须完全位于真正的 RX text 尾部：

```text
0x00313910 .. 0x00314000
```

verifier 额外要求：

```text
0x0036A000 .. 0x003AC000
```

整个 mapped data image 必须和原版逐字节完全一致。

---

## 3. V2：只保留一个 Hook

V1 使用 download callback marker + BankDataSync hook。

V2 发现 marker 完全没有必要，因为原版 `BankDataSyncState_Update` 本身已经保存完整异步完成状态。

唯一 Hook：

```text
BankDataSyncState_Update
0x002AF460
```

原版函数开头：

```asm
002AF460  push {r4-r6,lr}
002AF464  mov  r4,r0
002AF468  ldrb r1,[r0,#0x40]
...
```

补丁只把第一条 `push` 改成 branch，trampoline 自己先执行同样的 `push`，因此从 `+4` 返回时原版 stack frame 完全一致。

---

## 4. 直接使用原版 state 判断下载完成

逆向 `BankDataSyncState_Update` 后确认：

```text
state + 0x10  = substate (u32)
state + 0x40  = async callback status byte
state + 0x41  = special/full-download path flag
```

原版 case 2 的核心逻辑：

```c
if (state[0x40] == 1) {
    state[0x40] = 0;
    if (state[0x41] != 0)
        goto state10;
    next = 3;
}
```

因此 V2 的 Apply gate 定义为：

```text
substate       == 2
callbackStatus == 1
specialFlag    == 0
```

即：

```c
OfficialBulk_ShouldProcessState(2, 1, 0) == true
```

其它组合全部 false。

这有三个优点：

1. 不需要任何自定义全局 pending byte；
2. 不需要 Hook async download callback；
3. `specialFlag != 0` 的特殊/HOME 路径天然被排除。

处理发生在原版清除 `state+0x40` 之前，因此只会触发一次；返回原版后 callback byte 被原版消费，不会下一帧再次 Apply。

---

## 5. ARM → Thumb 紧凑 payload

真正安全的 RX padding 只有：

```text
0x00313910 .. 0x00314000
= 1776 bytes
```

V1 的 ARM runtime + core 总体太大，因此 V2 改成：

- 极小 ARM trampoline；
- 极小 ARM TLS helper；
- 主要 C runtime/core 编译成 Thumb；
- production 把 runtime + core 合并到同一 translation unit，让编译器 internalize/inlining；
- 所有 production helper 设为 internal static，仅 `OfficialBulkSync_Process` 保留入口。

当前 armips 实际占用：

```text
1660 / 1776 bytes
```

剩余约：

```text
116 bytes
```

### 5.1 ARM dispatch

位于：

```text
0x00313910
```

逻辑：

```asm
push {r4-r6,lr}               ; 重放原版 prologue
mov  r4,r0                    ; 保存 state
ldr  r12,=OfficialBulkSync_Process+1
blx  r12                      ; 进入 Thumb runtime
mov  r0,r4
b    BankDataSyncState_Update+4
```

### 5.2 TLS command-buffer bridge

ARMv6K Thumb 不能直接使用本项目 raw IPC 所需的 CP15 `mrc p15,...c13`，所以保留 3 条 ARM helper：

```asm
mrc p15,0,r0,c13,c0,3
add r0,r0,#0x80
bx  lr
```

Thumb C 通过 interworking 调用该 helper。

---

## 6. BankObject 获取

处理函数：

```text
OfficialBulkSync_Process(state)
```

先做 state gate，然后：

```c
flow   = *(u8 **)(state + 8);
object = flow ? *(u8 **)(flow + 0xCC) : 0;
body   = object + 8;
```

要求：

```text
object != NULL
*(u32 *)object == 0x003626FC
u16(body + 0x15C) == 2
u16(body + 0x15E) == 100
```

不满足时直接返回，原版 BankDataSync 流程继续。

---

## 7. Bank v1.5 主布局

```text
完整 current size       0xBB518
PKHeX Bank7 view        0xACA48
主 Box 起点             0x17C
100 Box 末端            0xAAF14
Box 数                  100
slot/Box                30
PKM stored size         0xE8
Box metadata            0x26
Box stride              0x1B56
Tag[3000] 起点          0xACA44
SourceSoftware 起点     0xB4AA0
Timestamp 起点          0xB5658
```

index：

```text
index = box * 30 + slot
```

parallel metadata：

```text
tag       = 0xACA44 + index
source    = 0xB4AA0 + index
timestamp = 0xB5658 + index*8
```

---

## 8. `bulk_import.bin` 契约

路径：

```text
SD:/3ds/Bank/bulk_import.bin
```

支持：

```text
0xACA48 PKHeX Bank7 view
0xBB518 full Bank image
```

但无论输入类型，联网实现只信任：

```text
0x17C .. 0xAAF14
```

即主 100 Box 的：

```text
Pokémon records + Box metadata
```

下列 bulk 字段永远忽略：

```text
Header / account identity
Transfer Box
Tag
SourceSoftware
Timestamp
source summary
NKZT
counters
tail
remote/session state
```

文件生命周期严格只读：不删除、不重命名、不覆盖、不回写。

---

## 9. Slot-aware merge

逐 slot 比较 fresh server record 与 bulk record。

### 9.1 unchanged

```text
PKM 相同
→ 不写 PKM
→ 保留 server tag/source/timestamp
```

### 9.2 empty → occupied

```text
写入 bulk PKM
→ tag = 当前联动游戏 format
→ source = 当前联动 software getter
→ timestamp = stock time helper
```

### 9.3 occupied → occupied changed

```text
替换 PKM
→ 刷新 tag/source/timestamp
```

### 9.4 occupied → empty

```text
清空 PKM
→ 保留 server 历史 tag/source/timestamp
```

真实 Bank 基线中大量空槽仍有历史 metadata，因此 V1/V2 都不把空槽 metadata 自动归零。

### 9.5 Box metadata

每 Box 的 `0x26` metadata 从 bulk 复制。

---

## 10. metadata 由 stock runtime 取得

### 10.1 current profile

```text
Game registry slot  0x003AB90C
GameModelActive      0x00233A6C
```

```c
registry = *0x003AB90C;
model = GameModelActive(*(registry + 0x1C));
profile = model[8];
```

### 10.2 format tag

当前映射：

```text
profile 1..4 → tag 0
profile 5..8 → tag 1
```

服务器 round-trip 前仍需通过单 Pokémon 实机确认。

### 10.3 source software

```text
Gen7-like profile:
    model + 0x74304

Gen6-like profile:
    model + 0x129AC
```

调用对象 vtable `+0x0C` getter，直接获取当前联动 software ID，不从 Pokémon Origin Game 推断。

### 10.4 timestamp

复用 stock helper：

```text
0x00234648 TimeContainerInit
0x001D3BF4 TimeQuery
0x001F2BD4 TimePack
```

避免 patch 自己实现 Bank 时间编码。

---

## 11. Fresh server backup

任何 bulk mutation 前，完整保存：

```text
/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

长度：

```text
0xBB518
```

只有 backup 完整写入并 close 成功后才允许 bulk Apply。

bulk 中途 short-read / FS error 时 runtime 可能已经部分修改，因此立即从刚生成的 fresh backup 恢复完整 `0xBB518`。

---

## 12. 原版 Save / Upload 不 Hook

V2 不修改：

```text
BankSaveState_Update
BankSave_SerializeAndStage
BankRemote_StageFileUpdate
PrepareUpdateBankObject
HPP/HTTP upload
CompleteUpdateBankObject
Commit/Rollback
HOME transfer state 28
```

所以补丁只产生一个 runtime candidate BankObject；真正上传仍由原版 Bank 自己完成。

---

## 13. V2 IPS 允许修改范围

`verify_official_bulk_sync.py` 现在只允许：

```text
0x002AF460 .. 0x002AF464
    BankDataSyncState_Update 单一 Hook

0x00313910 .. 0x00314000
    RX text tail payload
```

除此以外任何 byte diff 都失败。

特别强制：

```text
0x0036A000 .. 0x003AC000
```

整个 mapped data image 必须和原版完全一致，永久防止再次出现 V1 的 `.data cave` 错误。

原版 Bank v1.5 `.code` SHA-256：

```text
2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

verifier 还执行 IPS replay，要求：

```text
base + IPS == armips patched .code
```

逐字节一致。

---

## 14. Build 架构

production：

```text
official_bulk_sync_prod.c
    #include official_bulk_sync_core.c
    #include official_bulk_sync.c
```

定义：

```text
OFFICIAL_BULK_RUNTIME
OFFICIAL_BULK_INTERNAL
OFFICIAL_BULK_THUMB_RUNTIME
```

使 helper 在 production translation unit 内部化并压缩。

ARM target：

```text
-march=armv6k
-mthumb
-mfloat-abi=soft
-ffreestanding
-Wall -Wextra -Werror
```

Host test 仍独立编译 `official_bulk_sync_core.c`，不影响测试 API。

---

## 15. 自动测试

Host contract test 覆盖：

```text
0xACA48 / 0xBB518 size
header validation
unchanged metadata preserve
empty→occupied metadata generation
occupied→occupied refresh
occupied→empty historical metadata preserve
Box metadata
backup path
Gen6/Gen7 tag mapping
native state gate:
    (2,1,0) true
    (2,1,1) false
    (2,0,0) false
    (3,1,0) false
```

GitHub Actions：

```text
host test
ARMv6K Thumb GCC -Werror
unexpected __aeabi division helper check
payload size budget check
```

本地：

```text
armips build
IPS replay verifier
mapped data unchanged verifier
43 Python regression tests
```

---

## 16. 当前修正版静态构建

最近本地 V2 构建：

```text
armips area:
1660 / 1776 bytes
```

当前 preview `code.ips` SHA-256：

```text
EEC96762F460534E42D7C058A5140DB1D36FD999B14DC484D5BACECD50AA7CED
```

该 hash 只对应当前 commit/build；后续 payload 变化时应重新记录。

---

## 17. D6H 官方服务器验证顺序

不要从 120/3000 只直接开始。

```text
H0  无 bulk / no-op
H1  1 Pokémon
H2  30 Pokémon
H3  300 Pokémon
H4  3000 slots
H5  HOME transfer
```

每一步保存：

```text
fresh timestamp backup
bulk_import.bin SHA-256
server_after redownload
structured diff
```

H1 最关键：

```text
官方 fresh download
→ Apply 1 Pokémon
→ 原版 Save
→ 完整退出
→ 再登录
→ 官方 redownload
→ 验证 PKM/tag/source/timestamp/summary/NKZT/counters/tail
```

只有 H1 闭环后才扩大规模。

---

## 18. 结论

V2 的关键改变不是“修一个 UI 症状”，而是修正了架构假设：

```text
文件里是 0 ≠ 运行时没人使用
```

因此当前架构严格限定为：

```text
一个 native state hook
+
一个真正 RX text tail
+
零自定义全局 scratch
+
零 .data/BSS patch
```

这既解决 SM/USUM 游戏列表消失的根因，也让 normal Bank / HOME / Save 的原版全局状态保持不被 payload 静态覆盖。
