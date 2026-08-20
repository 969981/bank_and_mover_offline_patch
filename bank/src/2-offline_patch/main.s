.3ds
.arm
.relativeinclude on

.include "../../include/symbol.inc"

.definelabel OfflinePatch_CodeStart, 0x00313A40
.definelabel OfflinePatch_CodeEnd,   0x00314000
.definelabel OfflinePatch_PayloadStart, AccountTicketState_Update + 4
.definelabel OfflinePatch_PayloadEndLimit, 0x002B14E0

.open "../../00040000000C9B00.code", "../../build/2-offline_patch/00040000000C9B00.code", 0x00100000

// Replace network-dependent business states with synchronous local states.
// 用同步本地状态替换依赖网络的业务状态。
.org NetworkConnectionState_Update
    b OfflinePatch_NetworkUpdate
// Keep the native message and state-timer initialization, force the available
// branch, and skip allocation of the real remote connection job.
// 保留原版消息和状态计时器初始化，强制走可用分支，并跳过真实远端连接作业的分配。
.org NetworkConnection_AvailabilityCall
    mov r0,#1
.org NetworkConnection_SkipRemoteJob
    mov r0,#0
    str r0,[r4,#0x38]
    b NetworkConnectionState_Initialize + 0x5C
.org InitialRemoteRecordState_Update
    b OfflinePatch_InitialRemoteRecordUpdate
.org AccountTicketState_Update
    b OfflinePatch_TicketUpdate
.org BankDataSyncState_Update
    b OfflinePatch_BankDataSyncEntry

// Keep the native game check and post-selection connection screen. Route both
// metadata branches into that screen, then complete its remote transaction
// locally before entering the native local metadata phase.
// 保留原版游戏检查和选定游戏后的连接界面。让两个元数据分支都进入该界面，
// 再于本地完成其远端事务并进入原版的本地元数据阶段。
.org BankFlow_PostSelectionMetadataPath
    mov r0,#17
.org PostSelectionConnectionState_Update
    b OfflinePatch_PostSelectionConnectionUpdate

// Keep the stock disconnect screen and final cleanup, but skip allocation of
// the real disconnect job and complete its first phase locally after 1.5 s.
// 保留原版断开提示界面和最终清理，但跳过真实断开作业，并在 1.5 秒后于本地完成首阶段。
.org DisconnectCleanupState_Update
    b OfflinePatch_DisconnectWithLanguageSave
.org DisconnectCleanup_SkipRemoteJob
    mov r0,#0
    str r0,[r4,#0x38]
    b DisconnectCleanupState_Initialize + 0x78

// State 9 keeps the original first-use UI, account-ID acquisition, localized
// box-name initialization and creation date. Only remote job creation/upload
// are replaced. A synchronous local commit advances directly to state 8.
// state 9 保留原版首次使用界面、账户 ID 获取、本地化盒名初始化和创建日期；
// 仅替换远端作业创建与上传，同步本地提交成功后直接进入 state 8。
.org BankCreateState_Update + 0x58
    mov r0,#1
    b BankCreateState_Update + 0x238
// After the three stock first-use messages, skip only the remote record-ID
// acquisition substates 4-5. Continue at substate 6 so the native empty-object,
// localized box-name, and creation-date initializer still runs before the
// local write hook.
// 原版三段首次使用提示结束后，只跳过远端记录 ID 获取子状态 4-5。继续进入
// 子状态 6，使原版空对象、本地化盒名及创建日期初始化仍在本地写入钩子前执行。
.org BankCreateState_Update + 0x1E4
    mov r0,#6
    b BankCreateState_Update + 0x238
.org BankCreateState_Update + 0x2F4
    bl OfflinePatch_CreateInitial
.org BankCreateState_Update + 0x2FC
    movne r0,#8

// Skip reward-server states after a normal Bank load. HOME remains unavailable
// and is redirected to language selection.
// 普通 Bank 载入后跳过奖励服务器状态；HOME 不可用并重定向到语言选择。
.org BankFlow_SelectNextState + 0x248
    moveq r0,#25
.org BankFlow_SelectNextState + 0x170
    beq OfflinePatch_RedirectHomeToLanguage
.org BankFlow_SelectNextState + 0x34C
    beq BankFlow_SelectNextState + 0x3B4

// State 21 is the stock return path after changing language. Its disconnect
// work remains native, but a blank appended message prevents the newly selected
// font from drawing the old-language disconnect line.
// state 21 是更改语言后的原版返回路径。其清理流程保持原样，但使用新增空白
// 文本，避免新语言字库绘制旧语言的断网提示。
.org ReturnToTitleState_Update + 0x168
    bl OfflinePatch_SelectDisconnectMessage

// Keep the complete stock game-save sequence. Replace remote stage, commit and
// rollback with a local tmp/bin/bak transaction and skip asynchronous waits.
// 保留完整的原版游戏保存序列。以本地 tmp/bin/bak 事务替换远端暂存、提交和
// 回滚，并跳过异步等待。
.org BankSaveState_Update + 0x84
    mov r0,#1
    b BankSaveState_Update + 0x47C
// The local stage write finishes synchronously. Keep state 2 as a nonblocking
// two-second display phase before continuing with the native game-save work.
// 本地暂存写入会同步完成。保留 state 2 作为非阻塞的两秒显示阶段，
// 然后继续执行原版游戏保存流程。
.org BankSaveState_Update + 0x104
    mov r0,r4
    bl OfflinePatch_SaveDisplayDelayUpdate
    b BankSaveState_Update + 0x5BC
.org BankSave_SerializeAndStage + 0x180
    bl OfflinePatch_Stage
.org BankSaveState_Update + 0x3B4
    bl OfflinePatch_Commit
.org BankSaveState_Update + 0x3C8
    mov r1,#13
    str r1,[r4,#0x10]
    b BankSaveState_Update + 0x5BC
.org BankSaveState_Update + 0x3F0
    bl OfflinePatch_Rollback
.org BankSaveState_Update + 0x408
    mov r1,#16
    str r1,[r4,#0x10]
    b BankSaveState_Update + 0x5BC

.org OfflinePatch_CodeStart
.area OfflinePatch_CodeEnd-OfflinePatch_CodeStart
OfflinePatch_RedirectHomeToLanguage:
    ldr r0,[r0,#0x10]
    ldr r0,[r0,#0x38]
    cmp r0,#0
    blne WaitingUi_Hide
    mov r0,#1
    pop {r4,pc}

OfflinePatch_SelectDisconnectMessage:
    ldrb r1,[r4,#0x3C]
    cmp r1,#0
    moveq r1,#0x0D
    movne r1,#0x60
    bx lr

// State 21 is the language-return variant. Copy the pending language fields
// into the stock persistent settings object before starting its native save
// transaction. Wait for completion, then continue through the ordinary
// offline disconnect delay.
// state 21 是语言返回分支。先把待提交语言字段复制到原版持久化设置对象，
// 再启动其原生保存事务；等待保存完成后，继续普通的离线断开延时。
OfflinePatch_DisconnectWithLanguageSave:
    push {r4,lr}
    mov r4,r0
    ldrb r1,[r4,#0x3C]
    cmp r1,#0
    beq @@disconnect
    ldr r1,[r4,#0x10]
    cmp r1,#0
    beq @@beginSave
    cmp r1,#1
    bne @@disconnect
    bl StateLocalSave_Poll
    cmp r0,#0
    beq @@pending
    cmp r0,#1
    bne @@failed
    mov r1,#2
    str r1,[r4,#0x10]
    mov r0,r4
    bl StateTimer_Reset
@@pending:
    mov r0,#0
    pop {r4,pc}
@@beginSave:
    ldr r3,[r4,#8]
    cmp r3,#0
    beq @@disconnect
    ldr r0,[r3,#0x74]
    ldr r2,[r3,#0xF0]
    cmp r0,#0
    cmnne r2,#0
    beq @@disconnect
    ldr r1,[r2,#4]
    cmp r1,#0
    beq @@disconnect
    ldrb r2,[r2,#8]
    bl LocalSettings_SetLanguage
    mov r0,r4
    // Use native save mode 0, matching the stock language-commit path.
    // 使用与原版语言提交路径一致的本地保存模式 0。
    mov r1,#0
    bl StateLocalSave_Begin
    mov r1,#1
    str r1,[r4,#0x10]
    mov r0,#0
    pop {r4,pc}
@@failed:
    mov r1,#3
    strb r1,[r4,#0x30]
    mov r0,#1
    pop {r4,pc}
@@disconnect:
    mov r0,r4
    bl OfflinePatch_DisconnectUpdate
    pop {r4,pc}
    .pool

// Load the local file once, then resume the original state at substate 6 so
// its account-metadata copy and selected-game save callbacks remain intact.
// 先载入一次本地文件，再从原版子状态 6 继续执行，以保留账户元数据复制和
// 所选游戏保存回调。
OfflinePatch_BankDataSyncEntry:
    ldr r1,[r0,#0x10]
    cmp r1,#6
    bcs @@resumeNative
    push {r0,lr}
    bl OfflinePatch_LoadBankData
    cmp r0,#0
    pop {r0,lr}
    beq @@loadFailed
    mov r1,#6
    str r1,[r0,#0x10]
@@resumeNative:
    push {r4,r5,r6,lr}
    b BankDataSyncState_Update + 4
@@loadFailed:
    mov r1,#3
    strb r1,[r0,#0x30]
    mov r0,#1
    bx lr
    .pool

// Keep recovery path strings in the remaining verified executable padding so
// the linked C payload still fits inside the replaced ticket-state body.
// 将恢复路径字符串放进剩余的已验证可执行空位，使链接后的 C 载荷仍能容纳在
// 被替换的票据状态函数体内。
.org 0x00313F80
OfflinePatch_BrokenBankPath:
    .asciiz "/3ds/Bank/bankdata.bin.break"
.org 0x00313FA0
OfflinePatch_BrokenBackupPath:
    .asciiz "/3ds/Bank/bankdata.bak.break"

.endarea

// The original ticket-state body is unreachable after the entry branch above.
// Store the linked payload in that verified function extent instead of growing
// the code image or writing into non-executable rodata.
// 入口被替换后，原票据状态函数体已不可达。把链接载荷存入该已验证函数范围，
// 不扩展代码镜像，也不写入不可执行的 rodata。
.org OfflinePatch_PayloadStart
.area OfflinePatch_PayloadEndLimit-OfflinePatch_PayloadStart
OfflinePatch_PayloadBegin:
    .importobj "../../build/2-offline_patch/offline_patch.o"
OfflinePatch_PayloadEnd:
.endarea

.close
