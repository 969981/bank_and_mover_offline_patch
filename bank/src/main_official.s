.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official Bulk Sync + Recovery C (Existing Lock Recovery).
// Keep every executable byte inside the verified RX text tail. Recovery C
// replaces only the two genuine state18 game-transaction mismatch branches.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

.definelabel RecoveryC_GameDataIdMismatch,      0x002A89D0
.definelabel RecoveryC_GameVersionMismatch,     0x002A89E0
.definelabel RecoveryC_State17MessageIdLoad,    0x002A970C

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Run before the stock state machine consumes its native callback status byte.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// Recovery C activates only on the two actual current-game transaction
// mismatch edges. Invalid-status paths and all ordinary matching recovery
// records retain stock behavior.
.org RecoveryC_GameDataIdMismatch
    bne OfficialExistingLock_GameMismatch
.org RecoveryC_GameVersionMismatch
    bne OfficialExistingLock_GameMismatch

// Recovery C deliberately routes the synthetic status=1 game record through
// stock state17 so stock Rollback + transactionPassword cleanup + game save all
// remain intact. Stock state17 initializes with message 0x0E (the interrupted /
// server-locked banner) before it has inspected the record or started Rollback,
// which is misleading for the C path. Reuse stock message 0x0C, the ordinary
// initial-connection/wait message, but preserve the full 0x0025DA24 UI helper.
.org RecoveryC_State17MessageIdLoad
    mov r1,#0x0C

.org OfficialBulk_CodeStart
.area OfficialBulk_CodeEnd-OfficialBulk_CodeStart
.arm

// The native BankDataSync state already tells us exactly when an ordinary
// game-linked Bank download finished: substate==2, callbackStatus==1 and
// specialFlag==0. The Thumb runtime checks those fields itself, so no global
// pending marker and no download-callback hook are needed.
//
// Important interworking rule: do not let the imported Thumb object call an
// ARM helper through R_ARM_THM_CALL. armips currently relocates that external
// Thumb->ARM call two bytes early on this payload. Fetch TLS here in ARM state
// and pass the command-buffer pointer as r1 instead.
OfficialBulk_BankDataSyncDispatch:
    push {r4-r6,lr}
    mov r4,r0
    mrc p15,0,r1,c13,c0,3
    add r1,r1,#0x80
    ldr r12,=OfficialBulkSync_Process+1
    blx r12
    mov r0,r4
    b BankDataSyncState_Update + 4
    .pool

.align 2
    .importobj "../build/official_existing_lock_recovery_arm.o"
.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
