# 第三步：原版与离线合并补丁

## 模式选择

标题界面默认使用**离线模式**。在标题界面按 `R` 键，可在**离线模式**与
**原版模式**之间切换。模式文字位于 HOME 选单帮助文字下方，使用与 Bank 补丁
相同的按键字形，并会立即刷新。

按 A、START 或触摸下屏进入软件时，画面所示模式会锁定为本次会话模式。离开
标题界面后，`R` 不再切换模式。

```text
标题界面
   ├── R ─► 离线模式 ◄────► 原版模式
   └── 开始／触摸
          │ 锁定当前模式
          ├── 离线 ─► 本地 bankdata.bin 与离线事务钩子
          └── 原版 ─► 未修改的官方联网与服务器流程
```

## 模式隔离

第二步离线补丁使用的每个代码位置都会先读取已锁定的会话标志。离线模式进入
既有本地实现；原版模式则精确重放被覆盖指令，或跳回原函数后续，包括网络可用性、
票据、合法性检查、银行数据下载、传送暂存、提交、回滚和断开流程。

原版文本条目保持不变。资源只追加两条标题文本及四条离线连接／保存文本；运行时
钩子仅在离线模式选择追加文本。LayeredFS 资源覆盖全部十种语言。

离线模式与第二步具有相同的使用条件和事务保障：必须已有有效的
`sd:/3ds/Bank/bankdata.bin`，且传送盒必须为空。Poke Mover 不创建新的银行文件。

## 编译产物

在 `mover` 目录执行 `make -C src/3-combine_patch`。Luma 文件生成于：

```text
release/3-combine_patch/luma/titles/00040000000C9C00/
├── code.ips
└── romfs/a/...
```

编译会校验受支持基底哈希、代码空位边界、钩子目标、IPS 还原结果，并确认所有
原版本地化文本均未被更改。

## 外部开源参考

离线部分沿用已经独立核实的第二步实现及其引用：
[zaksabeast/Transporter-Offline-Patch](https://github.com/zaksabeast/Transporter-Offline-Patch)、
[Transporter-PKSM-Bank-Patch 状态机笔记](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch/blob/master/TRANSPORTER_DOCS.md)，
以及 [devkitPro/libctru FS 接口](https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/services/fs.h)。
所有地址和原版模式续接位置均以当前 Poke Mover 二进制重新核实。
