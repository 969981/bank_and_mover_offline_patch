# Poke Mover 离线补丁设计

## 范围

离线补丁保留原程序的卡带扫描、筛选、转换及 Transfer Box 规范化逻辑，只把依赖服务端的许可检查、下载、暂存、提交和回滚状态替换为本地等价流程。

## 业务状态绕过

| 拟议补丁地址 | 目标转移 |
|---:|---|
| `0x00242D10` | 游戏选择后跳过 `CONNECT_ONLINE` |
| `0x00242D28` | 继续传送许可处理 |
| `0x00248CDC` | 跳过远端许可对象的建立 |
| `0x00248D58` | 进入本地完成处理 |
| `0x00245728` | 跳过 Gen 5 远端检查 |
| `0x002460B8` | 跳过 Gen 1/2 远端检查 |
| `0x002488A0`、`0x002483CC` | 进入原有初始化成功分支 |
| `0x0024A150` | 跳过远端事务准备 |
| `0x0024A3D8` | 进入完整文件本地提交处理 |

这些是业务状态转移，不用于替代所有 HTTPC 返回值。

## 本地载入

替代逻辑在 `0x00248D3C` 接管完整 state 1 分支，从 `/3ds/Bank/bankdata.bin` 精确读取并验证 `0xBB518` 字节，再写入原异步回调本应选择的最终状态。

载入流程复用 `0x0025C978` 的对象语义：保留 30 个卡带候选槽，载入完整 BankObject，并在文件内 Transfer Box 为空时恢复候选槽。修改 Transfer Box 时，每个 `0xE8` 记录必须与对应的 1 字节标签同步。

## 事务性本地保存

| 拟议 Hook 边界 | 替代行为 |
|---:|---|
| `0x0024A240` | 将完整序列化对象写入 `bankdata.tmp`，并核对精确写入量 |
| `0x0024A3E4` | 卡带保存成功后，将旧文件轮换为可恢复备份，再替换 `bankdata.bin` |
| `0x0024A420` | 卡带保存失败后作废临时文件，保留原 `bankdata.bin` |

替代分支按原语义写入异步完成字段。Mover 与 Bank 继续共用 `/3ds/Bank/bankdata.bin`，不引入 Mover 专用的长期存储格式。

目录不存在时创建 `/3ds/Bank`；所有 FS 句柄都必须关闭；短读和短写均判定失败；所有互相重叠的状态修改应输出到同一个 IPS。

## 参考来源

本文的总体状态机和离线绕过思路与下列公开项目进行了交叉对照：

- zaksabeast 的 [Transporter-PKSM-Bank-Patch](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch) 及其 [Transporter documentation](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch/blob/master/TRANSPORTER_DOCS.md)：用于参考状态机结构和面向补丁的控制流思路。
- zaksabeast 的 [Transporter-Offline-Patch](https://github.com/zaksabeast/Transporter-Offline-Patch)：用于参考公开的离线绕过设计及兼容性背景。

上述引用仅涉及总体思路。本文中的地址和版本相关行为均以当前 `00040000000C9C00.code` 为对象重新分析和交叉核对，不能直接套用于其他版本。本补丁目录未包含上述参考项目的源代码。

## 已知限制

- 需要清理的最小本地重试状态集合尚未确认。
- 完全离线的时间戳行为仍取决于尚未定位的逐槽时间戳生成逻辑。
