.3ds
.arm
.relativeinclude on

.include "../../include/symbol.inc"

.definelabel DownloadPatch_HookAddress, BankRemote_DownloadSuccessCallback + 0x14
.definelabel DownloadPatch_BankFlowPaddingInitAddress, 0x002A491C
.definelabel DownloadPatch_ReturnStateFlagInitAddress, 0x002A5D04
.definelabel DownloadPatch_DisconnectMessageHookAddress, ReturnToTitleState_Update + 0x168
.definelabel DownloadPatch_LocalDownloadMessage, 0x60
.definelabel DownloadPatch_SuccessDisconnectMessage, 0x61
.definelabel DownloadPatch_BlankDisconnectMessage, 0x62
.definelabel DownloadPatch_BankDataSyncInitializeMessageAddress, BankDataSyncState_Initialize + 0x18
.definelabel DownloadPatch_PostUseBankResult5TargetAddress, BankFlow_SelectNextState + 0x260
.definelabel DownloadPatch_PostUseBankResult6Or12TargetAddress, BankFlow_SelectNextState + 0x270
.definelabel DownloadPatch_NoSaveExitTargetAddress, BankFlow_SelectNextState + 0x370
.definelabel DownloadPatch_HomeResultBranchAddress, BankFlow_SelectNextState + 0x170
.definelabel DownloadPatch_ClearCommonUiLayers, 0x001D5F50
// Luma LayeredFS injects its own 0x114-byte payload at TextActualEnd after
// applying code.ips. Reserve and do not branch into that loader-owned range.
// Luma LayeredFS 会在应用 code.ips 后从 TextActualEnd 注入自身的 0x114 字节
// 载荷。保留该加载器占用区域，补丁不得跳入其中。
.definelabel DownloadPatch_CodeCaveStart, 0x00313A40
.definelabel DownloadPatch_PayloadStart, 0x00313B50
.definelabel DownloadPatch_CodeCaveEnd, 0x00314000

.open "../../00040000000C9B00.code", "../../build/1-download_patch/00040000000C9B00.code", 0x00100000

// The feature menu returns result 23 for its former HOME entry. In outer
// state 4, redirect only that result from HOME-download state 28 to the stock
// language-selection state 1. No shared confirmation-button logic is changed.
// 功能选单原 HOME 项返回结果 23。在外层 state 4 中，仅把该结果从 HOME
// 下载状态 28 重定向到原版语言选择状态 1，不修改任何共用确认按钮逻辑。
.org DownloadPatch_HomeResultBranchAddress
    beq DownloadPatch_RedirectHomeToLanguage

// Zero the complete BankFlow padding word. The original strb already writes
// zero to +0x1C; widening it initializes the marker byte at +0x1D as well.
// 将 BankFlow 的整个填充字初始化为零。原指令已向 +0x1C 写零；扩展为
// 四字节写入，同时可靠初始化 +0x1D 的补丁标记。
.org DownloadPatch_BankFlowPaddingInitAddress
    str r7,[r0,#0x1C]

// Preserve the complete pre-menu flow, including first-user Bank creation.
// Keep the original game selection, recovery, and post-selection download.
// State 12 normally sends result 5 to state 13 for points/rewards and results
// 6/12 to the Bank Box. Redirect all three to the stock no-save state 19.
// 保留进入选单前的完整流程，包括首次用户的官方 Bank 数据创建。
// 继续执行原版游戏选择、事务恢复和选择游戏后的 Bank 数据下载。
// state 12 原本把结果 5 送往 state 13 领取里程/奖励，把结果 6/12 送往
// Bank Box；补丁将三者统一重定向到原版“不保存”状态 state 19。
.org DownloadPatch_PostUseBankResult5TargetAddress
    bleq DownloadPatch_MarkResult5

.org DownloadPatch_PostUseBankResult6Or12TargetAddress
    beq DownloadPatch_MarkResult6Or12

// Passively capture a completed ordinary-Bank download only when the shared
// state's mode byte is zero. HOME mode 1 and every other mode skip local I/O.
// Resume the exact original callback without changing its result or state.
// 仅当共用状态的模式字节为 0 时，旁路捕获普通 Bank 的完整下载。HOME 的
// 模式 1 及其他模式均跳过本地 I/O，随后精确恢复原回调结果与状态。
.org DownloadPatch_HookAddress
    bl DownloadPatch_Trampoline

// Select a dedicated status message without replacing stock line 14 globally.
// Normal Bank mode uses line 96; HOME mode retains stock line 14.
// 选择专用状态文本而不全局替换原版第 14 行。普通 Bank 模式使用第 96 行；
// HOME 模式继续使用原版第 14 行。
.org DownloadPatch_BankDataSyncInitializeMessageAddress
    b DownloadPatch_SelectBankDataSyncMessage

// Transfer the download-only marker from unused BankFlow padding into unused
// padding of the newly created normal-disconnect state, then clear the source.
// 将下载专用标记从 BankFlow 的未用填充字节转入新建普通断网状态的未用
// 填充字节，随后立即清除源标记。
.org DownloadPatch_ReturnStateFlagInitAddress
    bl DownloadPatch_InitializeReturnStateFlag

// State 21 follows an in-session language change. Keep its disconnect task but
// use a blank line so the newly selected font never renders stale-language
// text. Select the completion line only for the marked first-item exit; every
// other normal disconnect retains stock line 13.
// state 21 用于运行中更改语言后的退出。保留其断网任务，但改用空白行，避免
// 新语言字库绘制旧语言文本。仅第一项完成后的标记退出使用完成文本；其他
// 普通断网继续使用原版第 13 行。
.org DownloadPatch_DisconnectMessageHookAddress
    bl DownloadPatch_SelectDisconnectMessage

.org DownloadPatch_CodeCaveStart
.area DownloadPatch_PayloadStart-DownloadPatch_CodeCaveStart
DownloadPatch_Trampoline:
    push {r0-r3,r12,lr}
    sub sp,sp,#8
    mrs r12,cpsr
    str r12,[sp]
    ldrb r0,[r4,#0x41]
    cmp r0,#0
    bne DownloadPatch_TrampolineRestore
    mov r0,r7
    bl DownloadPatch_SaveBankData
DownloadPatch_TrampolineRestore:
    ldr r12,[sp]
    msr cpsr_f,r12
    add sp,sp,#8
    pop {r0-r3,r12,lr}
    ldr r8,=0x000BB528
    bx lr
    .pool

DownloadPatch_RedirectHomeToLanguage:
    ldr r0,[r0,#0x10]
    ldr r0,[r0,#0x38]
    cmp r0,#0
    blne DownloadPatch_ClearCommonUiLayers
    mov r0,#1
    pop {r4,pc}

DownloadPatch_MarkResult5:
    mov r0,#1
    strb r0,[r4,#0x1D]
    mov r0,#0x13
    bx lr

DownloadPatch_MarkResult6Or12:
    mov r0,#1
    strb r0,[r4,#0x1D]
    b DownloadPatch_NoSaveExitTargetAddress

DownloadPatch_InitializeReturnStateFlag:
    strb r1,[r0,#0x3C]
    ldrb r2,[r4,#0x1D]
    strb r2,[r0,#0x3D]
    strb r1,[r4,#0x1D]
    bx lr

DownloadPatch_SelectBankDataSyncMessage:
    cmp r1,#0
    moveq r1,#DownloadPatch_LocalDownloadMessage
    movne r1,#0x0E
    sub sp,sp,#8
    str r1,[sp]
    bl MessageUi_Begin
    ldr r1,[sp]
    add sp,sp,#8
    ldr r0,[r4,#0x38]
    b BankDataSyncState_Initialize + 0x2C

DownloadPatch_SelectDisconnectMessage:
    ldrb r1,[r4,#0x3C]
    cmp r1,#0
    movne r1,#DownloadPatch_BlankDisconnectMessage
    bxne lr
    ldrb r1,[r4,#0x3D]
    cmp r1,#0
    moveq r1,#0x0D
    movne r1,#DownloadPatch_SuccessDisconnectMessage
    bx lr

.endarea

.org DownloadPatch_PayloadStart
.area DownloadPatch_CodeCaveEnd-DownloadPatch_PayloadStart
DownloadPatch_PayloadBegin:
    .importobj "../../build/1-download_patch/download_patch.o"
DownloadPatch_PayloadEnd:
.endarea

.close
