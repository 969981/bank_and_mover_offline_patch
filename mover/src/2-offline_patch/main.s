.3ds
.arm
.relativeinclude on

.include "../../include/symbol.inc"

.definelabel OfflinePatch_CodeStart, 0x0028D1B0
.definelabel OfflinePatch_CodeEnd,   0x0028E000
.open "../../00040000000C9C00.code", "../../build/2-offline_patch/00040000000C9C00.code", 0x00100000

// Replace only the online-facing state updates; the game-selection, conversion,
// confirmation, cartridge-save and disconnect states remain native.
// 仅替换面向在线服务的状态更新；游戏选择、转换、确认、卡带保存和断开状态保持原样。
.org MoverNetworkState_Update
    b OfflinePatch_NetworkUpdate
// Keep the native message and state-timer initialization, force the available
// branch, and skip allocation of the real remote connection job.
// 保留原版消息和状态计时器初始化，强制走可用分支，并跳过真实远端连接作业的分配。
.org MoverNetwork_AvailabilityCall
    mov r0,#1
.org MoverNetwork_SkipRemoteJob
    mov r0,#0
    str r0,[r4,#0x38]
    b MoverNetworkState_Initialize + 0x5C
.org MoverTicketState_Update
    b OfflinePatch_TicketUpdate
.org MoverRemoteCheckState_Update
    b OfflinePatch_RemoteCheckUpdate
.org MoverTransferEligibilityState_Update
    b OfflinePatch_EligibilityUpdate

// The native initializer has already selected the local-data message and reset
// its timer. Delay entry into cartridge reading/conversion for two seconds so
// the message remains readable without blocking rendering.
// 原版初始化函数已经选择本地数据提示并重置计时器。进入卡带读取和转换前
// 异步等待两秒，使提示可读且不阻塞画面刷新。
.org MoverGetPokemonState_Update
    b OfflinePatch_GetPokemonEntry

// Keep native cartridge reading, filtering, and conversion, but bypass the
// two embedded server legality requests so state 9 cannot wait for callbacks.
// 保留原版卡带读取、过滤和转换，但绕过其中两处服务器合法性请求，
// 避免 state 9 永久等待远端回调。
.org MoverGetPokemon_SkipGen5RemoteValidation
    b MoverGetPokemon_Gen5LocalContinuation
.org MoverGetPokemon_SkipGen12RemoteValidation
    b MoverGetPokemon_Gen12LocalContinuation

// The stock no-transfer state performs one more server transaction before
// disconnecting. Complete that transaction locally so rejection and cancel
// paths cannot wait forever for a remote callback.
// 原版“不传送”状态会在断开前再执行一次服务器事务。将该事务改为本地完成，
// 避免拒绝或取消路径永久等待远端回调。
.org MoverNoTransferState_Update
    b OfflinePatch_NoTransferUpdate

// Keep the stock disconnect screen and final cleanup, but skip allocation of
// the real disconnect job and complete its first phase locally after 1.5 s.
// 保留原版断开提示界面和最终清理，但跳过真实断开作业，并在 1.5 秒后于本地完成首阶段。
.org MoverDisconnectState_Update
    b OfflinePatch_DisconnectUpdate
.org MoverDisconnect_SkipRemoteJob
    mov r0,#0
    str r0,[r4,#0x38]
    b MoverDisconnectState_Initialize + 0x78

// The offline remote-check result is routed directly to the eligibility state,
// skipping the two remote recovery-transaction states.
// 离线远端检查结果直接进入许可状态，跳过两个远端恢复事务状态。
.org MoverFlow_RemoteCheckSuccessState
    moveq r0,11

// State 0 no longer allocates a remote job. The local stage operation is
// synchronous, so state 1 advances directly to the native cartridge-save state 3.
// 状态 0 不再分配远端作业。本地暂存同步完成，因此状态 1 直接进入原生卡带保存状态 3。
.org MoverSave_SkipRemoteJob
    mov r0,1
    b 0x0024A4C0
.org MoverSave_StageCall
    bl OfflinePatch_Stage
.org MoverSave_AfterStageState
    movne r0,3

// Local commit and rollback are synchronous; skip their callback-wait states.
// 本地提交和回滚均为同步操作；跳过对应的回调等待状态。
.org MoverSave_CommitCall
    bl OfflinePatch_Commit
.org MoverSave_AfterCommitState
    movne r0,0x0E
.org MoverSave_RollbackCall
    bl OfflinePatch_Rollback
.org MoverSave_AfterRollbackState
    movne r0,0x11

.org OfflinePatch_CodeStart
.area OfflinePatch_CodeEnd-OfflinePatch_CodeStart
OfflinePatch_PayloadBegin:
OfflinePatch_GetPokemonEntry:
    push {r0,lr}
    mov r1,#125
    lsl r1,r1,#4
    bl StateTimer_HasElapsed
    cmp r0,#0
    pop {r0,lr}
    moveq r0,#0
    bxeq lr
    push {r4-r11,lr}
    b MoverGetPokemonState_Update + 4
    .pool

    .importobj "../../build/2-offline_patch/offline_patch.o"
OfflinePatch_PayloadEnd:
.endarea

.close
