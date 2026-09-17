# Pokémon Bank 游戏联动、GameSaveAdapter 与 Game ↔ Bank 转移链分析

> 研究对象：Pokémon Bank `00040000000C9B00`，内部版本 v1.5。
>
> 本文基于原版 `code.bin` 静态分析、现有 `BankObject` / `bankdata v1.5` 研究，以及 `SaveBoxesToServer` 事务分析整理。重点回答：Bank 如何识别 XY/ORAS/SM/USUM、如何挂载各游戏 `main`、如何把游戏盒子中的 Pokémon 转为统一 `0xE8` record、如何与 Bank 3000 槽交换，以及最终如何回写游戏并提交服务器事务。
>
> **边界说明**：本文把“已由静态代码确认的函数地址 / 对象偏移”和“仍需动态实验确认的 raw `main` 物理偏移”严格分开。Bank 的实现主要通过游戏适配对象访问盒子，而不是在 Box UI 中直接使用 `main + 固定偏移`。

---

## 1. 总体结论

普通 Bank 联动与 Poké Transporter 最终都汇入同一个 `BankObject`，但入口不同。

普通 Bank：

```text
3DS Pokémon game
  -> built-in GameProfile registry
  -> mount selected game's SaveData archive
  -> open `main`
  -> generation-specific game save model
  -> game-side Pokémon wrapper
  -> 0xE8 Pokémon record + format metadata
  -> BankObject slot
  -> serialize complete 0xBB518
  -> remote stage
  -> save game `main`
  -> remote commit / rollback
```

Mover：

```text
BW/B2W2 or VC source
  -> Poké Transporter conversion/filter
  -> 30-slot Transfer Box
  -> same 0xBB518 BankObject
  -> stage
  -> save source game
  -> commit / rollback
```

因此，研究“游戏 -> Bank”时应拆成三层：

1. **GameProfile / SaveData 层**：识别游戏、挂载 archive、打开 `main`；
2. **GameSaveAdapter 层**：盒子、槽、record、代际兼容和游戏侧保存；
3. **BankObject / 事务层**：Bank 3000 槽、并行元数据、stage / commit / rollback。

---

## 2. Bank 内置的 8 个游戏 Profile

Bank 原版代码创建 8 个游戏 profile，并为每个 profile 建立独立 SaveData archive alias。

| Profile | 游戏 | Title ID | archive alias | save file |
|---:|---|---|---|---|
| 1 | Pokémon X | `0004000000055D00` | `xdata:` | `main` |
| 2 | Pokémon Y | `0004000000055E00` | `ydata:` | `main` |
| 3 | Omega Ruby | `000400000011C400` | `ordata:` | `main` |
| 4 | Alpha Sapphire | `000400000011C500` | `asdata:` | `main` |
| 5 | Pokémon Sun | `0004000000164800` | `sundata:` | `main` |
| 6 | Pokémon Moon | `0004000000175E00` | `mondata:` | `main` |
| 7 | Ultra Sun | `00040000001B5000` | `usndata:` | `main` |
| 8 | Ultra Moon | `00040000001B5100` | `umndata:` | `main` |

### 2.1 Profile 初始化关键函数

| 地址 | 暂定命名 | 已确认行为 |
|---:|---|---|
| `0x00106510` | `GameProfileRegistry_Init` | 初始化 8 个支持游戏 profile 及其相关对象 |
| `0x00232360` | `GameSaveModel_Create` | 根据 profile id `1..8` 创建游戏侧 save/model 对象 |
| `0x00233840` | `SaveArchive_Create` | 创建与 `xdata:/` 等 alias 对应的 archive/profile 对象 |
| `0x00233704` | `SaveArchive_BindMain` | 将 archive 对象、游戏 model、`main` 与 alias 绑定 |

代码结构表现为连续创建：

```text
profile 1 -> xdata:/main
profile 2 -> ydata:/main
profile 3 -> ordata:/main
profile 4 -> asdata:/main
profile 5 -> sundata:/main
profile 6 -> mondata:/main
profile 7 -> usndata:/main
profile 8 -> umndata:/main
```

这说明 Bank 不会盲扫 SD 卡寻找名为 `main` 的文件，而是先通过支持表确认具体软件，再打开该 Title 对应 SaveData archive。

---

## 3. 游戏可用性检测与 Active Profile

“使用宝可梦银行”后的游戏软件选择属于 Bank 外层 state 10。

| 地址 | 暂定命名 | 作用 |
|---:|---|---|
| `0x002ADC50` | `GameSelectState_Update` | state 10：使用 Bank 后的游戏选择流程 |
| `0x001D4DCC` | `GameProfile_IsAvailable` | 对 profile `1..8` 做可用性检测 |
| `0x00229DF0` | `GameProfile_SetActive` | 切换当前 active profile |

初始化流程会分别查询 profile `1..8` 的可用状态，再生成选择列表。选中后由 `GameProfile_SetActive` 切换当前游戏上下文。

概念流程：

```text
GameProfileRegistry
  -> IsAvailable(1)
  -> IsAvailable(2)
  ...
  -> IsAvailable(8)
  -> build selectable-game list
  -> user selects game
  -> SetActive(profileId)
```

### 3.1 对自动识别改造的意义

如果以后要做：

- 自动识别联动游戏版本；
- 修改游戏显示名；
- 增加兼容 profile；
- 让工具直接显示当前 active game；

优先 Hook / 扩展点应是：

```text
GameProfileRegistry_Init
GameProfile_IsAvailable
GameProfile_SetActive
GameSelectState_Update
```

而不是只改 Box UI 文本。

---

## 4. Gen6 / SM / USUM 的适配分支

`GameSaveModel_Create` 保存 profile id，并由两个 helper 对 profile family 分类。

| 地址 | 静态行为 | 推导 |
|---:|---|---|
| `0x0023234C` | `return type == 5 || type == 6` | Sun / Moon family |
| `0x00232338` | `return type == 7 || type == 8` | Ultra Sun / Ultra Moon family |

因此代码明确区分：

```text
1..4 = XY / ORAS / Gen6 family
5..6 = SM family
7..8 = USUM family
```

静态代码中还出现两组明显不同的数据区域选择：

| family | 已观察对象相对偏移 | 说明 |
|---|---:|---|
| Gen6 | `+0x129AC`、`+0x3564` | Gen6 save/model 内部数据区域 |
| Gen7 family | `+0x74304`、`+0x763EC` | SM/USUM 使用的更大数据区域 |

这些偏移当前应理解为 **Bank 内部 game model 对象相对偏移**，不能直接写成 `main` 文件物理偏移。

---

## 5. GameSaveAdapter 抽象

从 Bank 的使用方式看，可以把游戏侧逻辑抽象成：

```cpp
struct GameProfile {
    uint64_t titleId;
    const char* archiveAlias;
    const char16_t* saveName; // main
    uint8_t profileId;
    GameFamily family;
};

struct GameSaveAdapter {
    GameProfile* profile;
    void* saveModel;

    // 静态分析已经证明存在等价能力，实际虚表/函数仍继续命名
    BoxInfo GetBoxInfo(...);
    PokemonWrapper GetSlot(...);
    bool WriteSlot(...);
    bool SaveMain(...);
};
```

Box UI 不需要理解 XY/ORAS/SM/USUM raw save layout；它只操作 adapter 暴露出来的游戏盒子 / Pokémon wrapper。

---

## 6. Game-side Pokémon wrapper 与 `0xE8` record

Bank 游戏侧 Pokémon 不直接从 raw `main` 某个位置 memcpy 到服务器，而是：

```text
raw main
 -> generation-specific save model
 -> game-side Pokémon wrapper
 -> normalize / compatibility logic
 -> 0xE8 record
 -> Bank slot
```

### 6.1 wrapper copy

| 地址 | 暂定命名 | 已确认行为 |
|---:|---|---|
| `0x00127C8C` | `GamePokemon_CopyRecord` | 从游戏侧 Pokémon wrapper 复制一个完整 `0xE8` record 到目标缓冲区 |

静态代码中该路径使用固定长度：

```text
0xE8 = 232 bytes
```

Gen6 和 Gen7 的 boxed Pokémon record 都是 `0xE8`，因此仅靠 payload 长度无法区分其代际语义；Bank 另有独立 format tag。

---

## 7. Bank Box UI 与 Game ↔ Bank swap

Bank Box UI 外层入口：

| 地址 | 暂定命名 | 作用 |
|---:|---|---|
| `0x002A7094` | `BankBoxUI_Update` | state 25：Bank Box 主界面 |
| `0x002B9C94` | `GameBank_SwapSelection` | 盒子/槽位操作核心之一，处理 `0xE8` record 及并行 metadata |

### 7.1 不是简单 Deposit，而是双向 swap/move

从 `0x002B9C94` 的行为看，底层更接近：

```cpp
BankSlotBackup tmp = ReadBankSlot(bankBox, bankSlot);

WriteBankSlot(
    bankBox,
    bankSlot,
    gamePokemon,
    gameFormat,
    activeSourceGame,
    now
);

WriteGameSlot(
    gameBox,
    gameSlot,
    tmp.pokemon,
    tmp.format
);
```

所以：

### Bank 目标为空

```text
Game A -> Bank
empty  -> Game
```

表现为普通“存入”。

### Bank 目标已有 Pokémon

```text
Game A <-> Bank B
```

表现为直接交换。

这解释了为什么 UI 可以统一支持存入、取出、交换，而无需三套完全独立的 payload 搬运逻辑。

---

## 8. BankObject 的逻辑 slot 不是只有 `0xE8`

Bank v1.5 的完整 slot 应按四联字段理解：

```text
Pokemon record   0xE8
Format Tag       1 byte
Source Software  1 byte
Timestamp        8 bytes
```

### 8.1 serialized `bankdata` 地址

```text
index = box * 30 + slot

PKM:
0x17C + box*0x1B56 + slot*0xE8

Tag:
0xACA44 + index

Source:
0xB4AA0 + index

Timestamp:
0xB5658 + index*8
```

### 8.2 BankObject 内存与文件偏移差 8 bytes

BankObject 本身在 serialized body 前有对象级头，因此代码中常见：

```text
serialized file     BankObject memory
0x17C          ->   0x184
0xACA44        ->   0xACA4C
0xB4AA0        ->   0xB4AA8
0xB5658        ->   0xB5660
```

这解释了静态代码和文件 diff 工具中常见的 `+8` 差异。

---

## 9. bankdata v1.5 相关区域

| 文件偏移 | 长度 | 内容 |
|---:|---:|---|
| `0x000000` | `0x17C` | header / names / version / state |
| `0x00017C` | `100 × 0x1B56` | 100 个 Bank Box |
| `0x0AAF14` | `30 × 0xE8` | Transfer Box |
| `0x0ACA44` | `3000` | Bank format tags |
| `0x0AD5FC` | `30` | Transfer tags |
| `0x0AD61A` | `2` | reserved / alignment |
| `0x0AD61C` | `8 × 0x44` | 8 个 source-game summary |
| `0x0AD83C` | `0x7260` | Pokédex-like aggregate |
| `0x0B4A9C` | `4` | deposit / withdrawal counters |
| `0x0B4AA0` | `3000` | source software IDs |
| `0x0B5658` | `3000 × 8` | timestamps |
| `0x0BB418` | `0x100` | tail flags / reserved |

完整 current-format size：

```text
0xBB518
```

---

## 10. Format Tag 与 Source Software 必须分开

Format Tag 与 Source Software 是两个独立数组：

```text
0xACA44  -> 3000 format tags
0xB4AA0  -> 3000 source software IDs
```

因此逻辑上至少应区分：

```cpp
struct BankSlotLogical {
    uint8_t pokemon[0xE8];
    uint8_t formatTag;
    uint8_t sourceSoftware;
    uint64_t timestamp;
};
```

### 10.1 不应假设 `tag == 0` 表示 empty

legacy -> current 升级路径会：

- 保留已有 Pokémon records；
- 将 current-only tag/source/timestamp 区域初始化为默认值；
- 因此 occupied slot 可以暂时拥有 `tag=0`, `source=0`, `timestamp=0`。

后续应通过真实操作验证枚举值：

```text
legacy/default occupied
XY newly deposited
ORAS newly deposited
SM newly deposited
USUM newly deposited
empty
```

---

## 11. Gen6 -> Gen7 兼容层位置

现阶段静态结构支持如下架构判断：

```text
Bank slot payload + format tag
  -> target active GameProfile
  -> GameSaveAdapter compatibility / conversion
  -> target generation game-side wrapper
  -> write game slot
```

因此不能把 Bank 理解成“所有 Pokémon 一律保存为 PK7”。更符合代码结构的是：

```text
0xE8 payload
+ independent format/generation tag
+ source metadata
```

当向目标游戏写回时，再由目标 profile 的 adapter 做兼容性判断与必要转换。

### 当前仍需继续验证

- format tag 的完整枚举；
- Gen6 record 进入 SM/USUM 时具体转换函数；
- USUM -> XY/ORAS 的拒绝点；
- held item 清除 / 规范化位于 wrapper 还是 target writer；
- 特殊 form / move / ability compatibility 检查链。

---

## 12. “拖进 Bank”不等于已经上传服务器

Bank Box UI 修改的是：

```text
game save runtime model
+
BankObject runtime image
```

真正保存由 state 7 执行。

| 地址 | 暂定命名 | 行为 |
|---:|---|---|
| `0x002B1CF8` | `BankSaveTransaction_Update` | 保存 / stage / game save / commit / rollback 状态机 |
| `0x002B2320` | `BankSave_SerializeAndStage` | 开始完整对象序列化并进入远端暂存 |
| `0x002B2490` | `BankObject_SerializeForSave` | 完成 `0xBB518` 序列化 |
| `0x002B24A0` / `0x002A2504` | `Remote_StageBankObject` | 将新 BankObject 放入远端事务暂存 |
| `0x001D5D74` | `Remote_Commit` | 游戏保存成功后提交事务 |
| `0x001D5C28` | `Remote_Rollback` | 游戏保存失败 / 放弃时回滚 |

流程：

```text
serialize new 0xBB518
 -> remote STAGE
 -> save selected game's main
 -> success: COMMIT
 -> failure: ROLLBACK
```

这个顺序用于避免：

- 先保存游戏、后上传失败导致 Pokémon 丢失；
- 先正式提交 Bank、后游戏保存失败导致 Pokémon 复制。

---

## 13. 完整 Bank 下载路径

普通启动 state 8 主要查询远端记录和事务状态；选定游戏后进入 state 16 才下载完整 BankObject。

```text
0x002AF460 BankDataSyncState_Update
  -> 0x002A3550 request full BankObject
  -> 0x002D11B0 download-success callback
  -> BankObject::Load
  -> apply metadata
```

下载单位是完整：

```text
0xBB518
```

不是按 Box 分页请求。

---

## 14. Poké Transporter 的不同入口

Mover 与 Bank 使用相同的 `0xBB518` 格式，但它把候选 Pokémon 写到 Transfer Box。

### Transfer Box

```text
0xAAF14  30 * 0xE8 record
0xAD5FC  30 tag bytes
```

Mover 已知函数：

| 地址 | 作用 |
|---:|---|
| `0x0019A224` | load one Transfer slot + tag |
| `0x0019A6F4` | write record + tag and normalize |
| `0x0019A7E0` | clear slot + tag |
| `0x0019A858` | valid-record check |
| `0x0024D624` | count valid Transfer slots |
| `0x0025C978` | download full BankObject, preserve/restore local transfer candidates |
| `0x0024A0C4` | serialize / stage / save source / commit-or-rollback |

这说明跨代转换发生在本机 Mover，不是服务器帮忙把旧世代 Pokémon 转成新格式。

---

## 15. 当前确认的 GameSaveAdapter 地址清单

下面这张表作为后续 IDA/Ghidra 命名表使用。

| 地址 | 建议名称 | 状态 |
|---:|---|---|
| `0x00106510` | `GameProfileRegistry_Init` | Confirmed role |
| `0x00127C8C` | `GamePokemon_CopyRecord` | Confirmed `0xE8` record copy path |
| `0x001D4DCC` | `GameProfile_IsAvailable` | Confirmed role |
| `0x00229DF0` | `GameProfile_SetActive` | Confirmed role |
| `0x00232338` | `GameType_IsUSUM` | Confirmed boolean family check |
| `0x0023234C` | `GameType_IsSM` | Confirmed boolean family check |
| `0x00232360` | `GameSaveModel_Create` | Confirmed profile-dependent model ctor |
| `0x00233704` | `SaveArchive_BindMain` | Confirmed binding role |
| `0x00233840` | `SaveArchive_Create` | Confirmed archive object creation role |
| `0x002A7094` | `BankBoxUI_Update` | Confirmed state 25 |
| `0x002ADC50` | `GameSelectState_Update` | Confirmed state 10 |
| `0x002B9C94` | `GameBank_SwapSelection` | Confirmed box/slot record+metadata operation family |
| `0x002B1CF8` | `BankSaveTransaction_Update` | Confirmed state 7 transaction |

### 已确认对象偏移

```text
Gen6 model regions:
+0x3564
+0x129AC

SM / USUM model regions observed in family-dependent branches:
+0x74304
+0x763EC
```

这些是 **运行时 model/object 偏移**。

---

## 16. 尚未确认、不能伪造成“固定 main 地址”的项目

以下内容目前还不能安全写死：

| 项目 | 当前状态 |
|---|---|
| XY raw `main` Box 1 physical file offset | Pending |
| ORAS raw `main` Box 1 physical file offset | Pending |
| SM raw `main` Box 1 physical file offset | Pending |
| USUM raw `main` Box 1 physical file offset | Pending |
| raw save box stride | Pending direct Bank-code confirmation |
| box name physical file offset | Pending |
| box name runtime pointer accessor | Pending function naming |
| current game box index accessor | Pending function naming |
| game slot write-back function | Pending exact callee naming |
| game save dirty flag | Pending exact field/function naming |
| per-generation checksum/re-encryption commit | Pending exact call chain |

原因不是这些结构不存在，而是 Bank code 通过 adapter/model 间接访问。下一轮需要从 `0x002B9C94` 的 caller/callee 与 `0x00127C8C` 的 wrapper source 反向恢复具体 getter/setter。

---

## 17. 下一轮逆向任务：`0x002B9C94 -> 0x00127C8C -> GameSaveAdapter`

### R4.1 还原 `0x002B9C94` 参数语义

目标：给所有参数命名并确认：

```text
BankObject*
GameSaveAdapter*
bankBox
bankSlot
gameBox
gameSlot
selection width/height
operation flags
```

输出：

- function prototype；
- 每个参数的来源 caller；
- Bank slot address 计算；
- game slot object 获取链；
- temp backup buffer layout。

### R4.2 反向追 `0x00127C8C`

目标：确定 wrapper 中保存 `0xE8` record 的字段 / 指针，以及所有 caller。

需要确认：

```text
wrapper + ? -> record pointer
wrapper + ? -> format
wrapper + ? -> empty/valid
wrapper + ? -> game profile/type
```

### R4.3 找出 BoxInfo / BoxName accessor

从 Box UI 中对：

```text
box index
box name
slot array
current selected box
```

的读取追到 adapter。

输出目标：

```cpp
int GetBoxCount(GameSaveAdapter*);
int GetCurrentBox(GameSaveAdapter*);
const char16_t* GetBoxName(GameSaveAdapter*, int box);
PokemonWrapper* GetBoxSlot(GameSaveAdapter*, int box, int slot);
```

这里只在静态代码真的支持时才使用这些名称。

### R4.4 找出 WriteSlot -> SaveMain 链

从 swap 完成后一路追：

```text
WriteGameSlot
 -> set dirty
 -> generation save section rebuild
 -> checksum/encryption update
 -> FS write
 -> commit SaveData
```

并分别记录 XY/ORAS/SM/USUM 是否使用同一 writer。

### R4.5 动态验证 raw `main`

静态 adapter 结构确认后，再用 before/after：

```text
same save
move exactly one Pokémon from Box N Slot M
compare main before / after
```

验证：

- physical box base；
- stride；
- crypto/checksum side effects；
- box name region；
- current-box metadata；
- party / battle box 是否独立。

**不要反过来仅凭 raw diff 猜 adapter 字段。**

---

## 18. 对 Route A / `bulk_import.bin` 的影响

完整镜像编辑器仍应把 `0xBB518` 作为对象边界：

```text
PC bulk_import.bin
  = complete edited 0xBB518 image
```

应用时：

```text
fresh official BankObject downloaded from server
  + whitelist overlay:
      3000 PKM payloads
      format tags
      source software IDs
      timestamps (only where semantics confirmed)
      intended box metadata
  -> official serialize/stage/save/commit path
```

不应：

```text
memcpy stale header / account identity / transaction fields
```

也不应只构造：

```text
3000 * 0xE8
```

因为原版 swap 明确依赖并行 metadata。

---

## 19. 建议的后续工程接口

最终如果要在项目里实现可测试的游戏联动观察器，建议接口保持只读优先：

```cpp
typedef enum {
    GAME_X = 1,
    GAME_Y = 2,
    GAME_OR = 3,
    GAME_AS = 4,
    GAME_SUN = 5,
    GAME_MOON = 6,
    GAME_US = 7,
    GAME_UM = 8,
} BankGameProfileId;

typedef struct {
    uint8_t profile_id;
    uint64_t title_id;
    const char *archive_alias;
    const char16_t *save_name;
    bool available;
} BankGameProfileInfo;

typedef struct {
    uint8_t pkm[0xE8];
    uint8_t format_tag;
    bool valid;
} GameSlotSnapshot;
```

第一阶段只实现：

```text
ListProfiles
GetActiveProfile
GetBoxCount
GetBoxName
ReadGameSlot
ReadBankSlot
DiffSlot
```

等所有 getter 与结构都由静态 + 动态证据确认后，再考虑写入。

---

## 20. 当前研究状态总结

### 已完成

- [x] 8 个支持游戏 profile 与 Title ID 对应关系。
- [x] `xdata:/` / `ydata:/` / `ordata:/` / `asdata:/` / `sundata:/` / `mondata:/` / `usndata:/` / `umndata:/` 与 `main` 的绑定关系。
- [x] state 10 游戏选择流程定位。
- [x] active profile 设置点定位。
- [x] Gen6 / SM / USUM family 判定 helper。
- [x] game model 中观察到的 family-dependent 数据区域。
- [x] `0xE8` game-side record copy 路径定位。
- [x] Bank Box UI 与核心 swap/move 操作定位。
- [x] Bank slot 四联字段与 `bankdata` 地址对应。
- [x] Game change -> serialize -> stage -> game save -> commit/rollback 事务链。
- [x] Mover Transfer Box 与普通 BankObject 的汇合关系。

### 继续研究

- [ ] 完整恢复 `0x002B9C94` prototype 与所有 callees。
- [ ] 完整恢复 `0x00127C8C` wrapper layout。
- [ ] 定位 Box count / current box / Box name accessors。
- [ ] 定位 `GetBoxSlot` / `WriteBoxSlot`。
- [ ] 定位每代 game save dirty / checksum / encryption / FS commit 链。
- [ ] 用 before/after `main` 验证 XY/ORAS/SM/USUM physical box offsets。
- [ ] 完整枚举 Bank format tag 与 source software ID。
- [ ] 定位 Gen6 -> Gen7 转换与反向不兼容检查。

---

## 21. 与现有文档的关系

本文负责 **游戏联动 / GameSaveAdapter / Game ↔ Bank slot**。

其它主题继续参考：

- `code-analysis.zh-cn.md`：Bank 原版整体状态机与 BankObject 基础布局；
- `saveboxes-transaction-analysis.zh-cn.md`：`SaveBoxesToServer`、stage / commit / rollback；
- `bank-v15-bulk-import-roadmap.zh-cn.md`：完整镜像 Bulk Import 路线 A；
- `bank-v15-legacy-upgrade-analysis.zh-cn.md`：`0xACA48 -> 0xBB518` legacy/current 升级与 current-only metadata 初始化。

后续 R4 的所有新函数命名、参数恢复和 dynamic validation 结果优先追加到本文，再同步必要结论到 roadmap。