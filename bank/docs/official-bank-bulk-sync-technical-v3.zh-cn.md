# Pokémon Bank v1.5 Official Bulk Sync V3 技术说明

> 分支：`feature/official-bank-bulk-sync`
>
> 本文记录 V2 实机联动时 `undefined instruction` 的根因、机器码证据、V3 架构调整和后续验证要求。

## 1. V2 实机现象

V2 已经修复了前一版 `.data` 区污染，因此 Sun/Moon/Ultra Sun/Ultra Moon 等游戏重新能够在 Pokémon Bank 游戏选择界面正常显示。

但在正常联动游戏、进入 BankDataSync 路径时，实机发生：

```text
Exception type: undefined instruction
PC:            0x00313BB0
CPSR:          0x60000030
```

CPSR 中 T bit 为 1，说明异常发生在 Thumb 状态。

## 2. PC 精确定位

V2 payload 布局：

```text
0x00313910  OfficialBulk_BankDataSyncDispatch   ARM
0x0031392C  OfficialBulk_CommandBuffer          ARM
0x00313938  OfficialBulkSync_Process            Thumb
```

`OfficialBulkSync_Process` 内部为了执行 raw FS IPC，需要获取 TLS command buffer。ARMv6K Thumb 不能直接执行所需的 CP15 `MRC`，所以 V2 采用：

```text
Thumb C
→ R_ARM_THM_CALL
→ OfficialBulk_CommandBuffer (ARM)
```

实机 crash PC `0x00313BB0` 正好落在这次 Thumb `BLX` 的第二 halfword。

## 3. relocation 根因

V2 最终 IPS 在 `0x00313BAE` 的机器码：

```text
FF F7 BD EE
```

而用 `ld.lld` 对同样的：

```text
source = 0x00313BAE
ARM target = 0x0031392C
```

生成的正确 Thumb→ARM `BLX` 是：

```text
FF F7 BE EE
```

也就是说 armips `.importobj` 处理这个“导入 Thumb object 中的 `R_ARM_THM_CALL`，目标是 armips 汇编区里的 ARM symbol”时，relocation 结果少了 2 bytes。

结果等价于尝试跳到：

```text
0x0031392A
```

而不是：

```text
0x0031392C
```

`0x0031392A` 不是 ARM 指令边界，因此 ARM11 触发 `undefined instruction`。

这与实机寄存器完全吻合：异常发生在 BLX interworking 边界，而不是 Bank Pokémon 数据 merge、metadata 或服务器返回数据本身。

## 4. V3 修复原则

V3 不再让导入的 Thumb object 调用任何外部 ARM helper。

旧 V2：

```text
ARM dispatcher
→ BLX Thumb OfficialBulkSync_Process
   → Thumb R_ARM_THM_CALL
      → ARM OfficialBulk_CommandBuffer
```

V3：

```text
ARM dispatcher
→ ARM MRC p15 直接获取 TLS
→ r1 = TLS + 0x80 command buffer
→ BLX Thumb OfficialBulkSync_Process(state, commandBuffer)
```

因此彻底删除：

```text
OfficialBulk_CommandBuffer
```

和对应的：

```text
R_ARM_THM_CALL OfficialBulk_CommandBuffer
```

## 5. V3 dispatcher

入口仍然只有：

```text
BankDataSyncState_Update = 0x002AF460
```

V3 dispatcher 逻辑：

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

这里：

```text
r0 = BankDataSync state
r1 = FS command buffer
```

Thumb C 不再需要 CP15 bridge。

## 6. V3 runtime function signature

V2：

```c
int OfficialBulkSync_Process(void *stateVoid);
```

V3：

```c
int OfficialBulkSync_Process(
    void *stateVoid,
    volatile u32 *commandBuffer
);
```

随后：

```text
writeSnapshot
→ setSize
→ raw FSFILE SetSize IPC
```

直接使用从 ARM dispatcher 传进来的 command buffer。

## 7. V3 构建布局

当前 GCC ARMv6K Thumb object 通过 CI 编译后，再由 armips 导入真实 RX text tail。

最终 armips 结果：

```text
payload used: 1615 / 1776 bytes
free:         161 bytes
```

关键 symbol：

```text
0x00313910  OfficialBulk_BankDataSyncDispatch
0x003139D4  OfficialBulkSync_Process
0x00314000  text mapped end
```

整个 payload 仍严格位于：

```text
0x00313910 .. 0x00314000
```

没有使用 `.data` 作为代码或 scratch。

## 8. V3 静态安全边界

允许修改范围仅：

```text
0x002AF460 .. 0x002AF464
0x00313910 .. 0x00314000
```

同时 verifier 强制：

```text
0x0036A000 .. 0x003AC000
```

整个 mapped data image 与原版逐字节一致。

另外 CI 永久增加两类 regression guard：

```text
1. 禁止 __aeabi_* division runtime helper
2. 禁止 OfficialBulk_CommandBuffer 未定义符号或 relocation
```

这样以后不会再次生成相同的 Thumb→ARM external relocation。

## 9. V3 编译验证

GitHub Actions：

```text
host merge/state contract       PASS
ARMv6K Thumb -Werror            PASS
runtime helper rejection        PASS
cross-ISA helper rejection      PASS
text-tail size budget           PASS
ARM object artifact upload      PASS
```

本地使用 CI 生成的 GCC object 进行：

```text
armips assembly                 PASS
IPS generation                  PASS
IPS replay verifier             PASS
.data byte-for-byte check       PASS
```

当前 `code.ips`：

```text
size: 1635 bytes
SHA-256:
9D17E1126316878497E07D1D1234860227B031EB26A9B9100C82B24806E3BDEE
```

## 10. 实机验证顺序

### H0

暂时移走：

```text
/3ds/Bank/bulk_import.bin
```

确认：

```text
游戏列表正常
→ 任意 Gen6/Gen7 游戏可正常联动
→ 不发生 undefined instruction
```

### H1-preview

恢复 `bulk_import.bin`，但先不保存：

```text
正常联网
→ state 16 下载
→ 生成 fresh backup
→ runtime apply bulk
→ Bank UI 显示正确
```

### H1-round-trip

只用 1 只 Pokémon：

```text
Apply
→ 原版保存
→ 退出
→ 重新联网下载
→ 确认服务器 Bank 持久化
```

之后才逐步扩大：

```text
1 → 30 → 300 → 3000
```

## 11. 结论

V2 的 crash 不是 Pokémon 数据格式问题，也不是 metadata writer 问题，而是一个明确的 ARM/Thumb interworking relocation 错误。

V3 通过把 TLS/command-buffer 获取前移到 ARM dispatcher，完全消除了这类跨 ISA external relocation，同时继续保持：

```text
原版联网
原版游戏选择
原版 Save/Upload
原版 HOME
bulk_import.bin 只读
fresh server Bank 先备份
slot-aware merge
```
