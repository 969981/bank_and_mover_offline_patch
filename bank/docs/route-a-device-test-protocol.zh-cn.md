# Pokémon Bank Route A D5 实机验证协议

本文用于验证当前 `research/saveboxes-transaction-analysis` 分支的 Route A V0：

```text
bankdata.bin
  + bulk_import.bin
        ↓
Offline Mode Load
        ↓
只覆盖 runtime 0x17C..0xAAF14 主 100 Box
        ↓
原版 Bank Box UI
        ↓
原版 Offline Save
        ↓
restart / reload
```

当前版本不自动删除 `bulk_import.bin`，因此**验证保存持久化前必须先把 bulk 文件移走**，否则第二次启动会再次应用 bulk，无法证明 `bankdata.bin` 本身已经保存成功。

## 1. 测试前备份

至少保存：

```text
bankdata_before.bin
bankdata.bak_before.bin   （若存在）
```

不要覆盖唯一备份。

3DS SD 路径：

```text
sd:/3ds/Bank/bankdata.bin
sd:/3ds/Bank/bankdata.bak
sd:/3ds/Bank/bulk_import.bin
```

## 2. PC 工具目录

以下命令假设当前目录为：

```text
ViewerForBankdata
```

先验证 baseline：

```powershell
python .\tools\bankbulk.py validate "D:\BankTest\bankdata_before.bin"
```

## 3. T0：no-op bulk，先验证整条代码路径

T0 的 `bulk_import.bin` 与 baseline 完全相同。

生成：

```powershell
python .\tools\bankbulk.py build `
  "D:\BankTest\bankdata_before.bin" `
  -o "D:\BankTest\bulk_import.bin"
```

理论 expected：

```powershell
python .\tools\bankbulk.py apply-v0 `
  "D:\BankTest\bankdata_before.bin" `
  "D:\BankTest\bulk_import.bin" `
  -o "D:\BankTest\expected_after_apply.bin"
```

T0 时 expected 应与 baseline byte-identical。

### 3DS 操作

1. 把 `bulk_import.bin` 放到 `sd:/3ds/Bank/`。
2. 启动当前 research patch 的 **Offline Mode**。
3. 正常选择兼容游戏并进入 Bank Box UI。
4. 确认 Box 内容与原来一致，没有乱码、空箱异常、崩溃或卡死。
5. 正常执行“保存并退出”。
6. 完全退出 Bank。
7. **把 `sd:/3ds/Bank/bulk_import.bin` 移走或改名**。
8. 再次启动 Offline Mode，确认 Bank 能正常重载。
9. 把此时的 `bankdata.bin` 复制回 PC，命名为 `bankdata_T0_saved.bin`。

### 自动验收

```powershell
python .\tools\bankbulk.py verify-v0 `
  "D:\BankTest\bankdata_before.bin" `
  "D:\BankTest\bulk_import.bin" `
  "D:\BankTest\bankdata_T0_saved.bin" `
  --json "D:\BankTest\T0_verify.json"
```

默认判定：

- 主 100 Box 与理论 expected 完全一致：PASS；
- source/tag/time/NKZT/counters/tail 等主 Box 外区域若被 stock save 改写：仍可 PASS，但会单独报告；
- 主 Box payload 或 box metadata 与 expected 不一致：FAIL，exit code `3`。

如果要检查全 `0xBB518` 必须一字节不变：

```powershell
python .\tools\bankbulk.py verify-v0 `
  "D:\BankTest\bankdata_before.bin" `
  "D:\BankTest\bulk_import.bin" `
  "D:\BankTest\bankdata_T0_saved.bin" `
  --strict
```

`--strict` 失败并不自动说明 Route A 失败；它可能只是揭示 stock save 正常更新了 current-only metadata。这些变化正是 R4/R5/R6 的研究输入。

## 4. T1：单槽 overwrite

T0 通过后再做 T1。

为了避免 R1/R2/R3 尚未完全确认的“空槽新建 metadata”问题，T1 优先选择：

```text
一个当前已经 occupied、且 tag/source/timestamp 都已有历史值的槽
```

不要第一步就使用全零空槽。

流程：

1. 从 `bankdata_before.bin` 导出 PKHeX view：

```powershell
python .\tools\bankbulk.py export-pkhex `
  "D:\BankTest\bankdata_before.bin" `
  -o "D:\BankTest\T1_pkhex_view.bin"
```

2. PKHeX 打开 `T1_pkhex_view.bin`。
3. 只替换一个已占用槽中的 Pokémon，不移动其它槽、不改 Box 名称。
4. PKHeX 保存为 `T1_pkhex_view_edited.bin`。
5. 回灌：

```powershell
python .\tools\bankbulk.py import-pkhex `
  "D:\BankTest\bankdata_before.bin" `
  "D:\BankTest\T1_pkhex_view_edited.bin" `
  -o "D:\BankTest\bulk_import.bin"
```

6. 生成理论 expected：

```powershell
python .\tools\bankbulk.py apply-v0 `
  "D:\BankTest\bankdata_before.bin" `
  "D:\BankTest\bulk_import.bin" `
  -o "D:\BankTest\T1_expected.bin"
```

7. 先用 diff 确认 PC 侧修改范围只有预期槽：

```powershell
python .\tools\diff_bank_file.py `
  "D:\BankTest\bankdata_before.bin" `
  "D:\BankTest\T1_expected.bin" `
  --json "D:\BankTest\T1_expected_diff.json"
```

8. 按 T0 相同 3DS 流程：进入 UI 检查 → 正常保存 → 退出 → 移走 bulk → 重启 → 拿回 saved Bank。
9. `verify-v0` 验收。

## 5. T2：empty → occupied

T1 通过后才做。推荐使用已确认的干净测试区：

```text
Box 60 Slot 1~5
```

此前 baseline 分析中这些槽的 Pokémon/tag/source/timestamp 都为零。

这个测试的目的不仅是 D5，还直接服务 R1/R2/R3：观察原版 UI/save 面对 payload-only 新槽时是否会自动生成或修正：

```text
tag
source software
timestamp
counters
source summary
NKZT
tail
```

如果 UI 能显示且 save/reload 后主 Box 正确，但 metadata 仍为 0，说明这些字段至少不是本地 loader/save 的硬性必需条件；是否适合 Official/HOME 仍需后续 controlled experiment。

## 6. T3：occupied → empty

选择一只可恢复的测试 Pokémon，从 bulk/PKHeX view 中清空该槽。

重点观察：

```text
PKM 是否清空
旧 tag/source/timestamp 是否继续保留
counter 是否变化
stock save 是否改写任何 current-only 区域
```

这将验证真实 baseline 中“空槽仍保留历史 metadata”的行为能否由当前路径复现。

## 7. T4/T5/T6 扩量

依次：

```text
T4  1 Box
T5  10 Boxes
T6  100 Boxes
```

每次都遵守：

```text
before
+ bulk
-> expected
-> 3DS apply
-> manual inspect
-> save
-> remove bulk
-> restart/reload
-> saved
-> verify-v0
```

不要直接从 T0 跳到 100 Box。

## 8. R4/R5/R6 差分采集

每次 saved image 都额外跑：

```powershell
python .\tools\diff_bank_file.py `
  "D:\BankTest\Tn_expected.bin" `
  "D:\BankTest\Tn_saved.bin" `
  --json "D:\BankTest\Tn_stock_save_diff.json"

python .\tools\r456_classifier.py `
  "D:\BankTest\Tn_saved.bin" `
  --json "D:\BankTest\Tn_r456.json"
```

这样可以把：

```text
Bulk Apply 造成的变化
```

和：

```text
原版 Bank save 自己派生/更新的变化
```

分开。

## 9. D6 门槛

只有在以下条件满足后才进入 Official Mode：

```text
T0 PASS
T1 PASS
至少一次 restart/reload PASS
主 Box saved == expected
没有无法解释的破坏性 current-only 变化
```

更推荐先完成 T2/T3，再开始 D6。

D6 第一轮仍限制为 **1 Pokémon**，并且使用 stock 官方下载、stock save transaction、重新下载后的 `server_after.bin` 做 round-trip diff；不自行构造 NEX/HPP transaction。
