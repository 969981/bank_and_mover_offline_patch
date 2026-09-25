.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official Bulk Sync + Recovery C4 (Persistent Existing-Lock Repair).
// Keep every executable byte inside the verified RX text tail. C4 replaces
// only narrow, machine-code-verified recovery/state-routing points.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

.definelabel RecoveryC_GameDataIdMismatch,      0x002A89D0
.definelabel RecoveryC_GameVersionMismatch,     0x002A89E0
.definelabel RecoveryC_State17CtorMarkerInit,   0x002A61C8
.definelabel RecoveryC_State17StatusLoad,       0x002A9518
.definelabel RecoveryC_State17StatusResume,     0x002A951C
.definelabel RecoveryC_State17PersistBlock,     0x002A95F0
.definelabel RecoveryC_State17StoreSubstate,    0x002A9618
.definelabel RecoveryC_State17SuccessResult,    0x002A966C
.definelabel RecoveryC_State17MessageIdLoad,    0x002A970C
.definelabel RecoveryC_StockGameSaveStart,      0x002B4AB4

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Run before the stock state machine consumes its native callback status byte.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// Recovery C4 activates only on the two actual current-game transaction
// mismatch edges. Invalid-status paths and all ordinary matching recovery
// records retain stock behavior.
.org RecoveryC_GameDataIdMismatch
    bne OfficialExistingLock_GameMismatch
.org RecoveryC_GameVersionMismatch
    bne OfficialExistingLock_GameMismatch

// state17 allocates 0x68 bytes and stock owns +0x60/+0x61 for callback status.
// +0x62 is unused by stock state17. Initialize the dword at +0x60 as
// 00 00 04 00 so ordinary state17 success still returns result=4 while keeping
// both stock callback bytes cleared. C4 changes only +0x62 to 3.
.org RecoveryC_State17CtorMarkerInit
    mov r1,#0x40000
    str r1,[r0,#0x60]

// Consume C4's RAM-only GameRecoveryRecord.status=3 before stock state17
// evaluates status. The helper restores stock status=1, marks +0x62=3, and
// routes directly to stock case5 (game-save stage) WITHOUT Commit/Rollback.
.org RecoveryC_State17StatusLoad
    b OfficialExistingLock_State17Status

// Stock case5 normally clears transactionPassword after a completed remote
// operation and then starts the game save. C4 reaches case5 before any remote
// operation, so only the C4 marker skips that clear. Ordinary stock state17
// still clears the password. The save call itself is the exact stock state17
// vtable +0x18 implementation at 0x002B4AB4.
.org RecoveryC_State17PersistBlock
    ldrb r2,[r4,#0x62]
    cmp r2,#3
    beq @@persist_call
    mov r1,#0
    str r1,[r0,#0x08]
    str r1,[r0,#0x0C]
@@persist_call:
    mov r1,#1
    mov r0,r4
    bl RecoveryC_StockGameSaveStart
    mov r0,#6

// Stock case7 is the successful terminal result. Ordinary state17 +0x62 is 4,
// reproducing stock behavior. C4 is 3, so a successful persist-only repair
// returns result=3 -> state20 clean disconnect. A failed game save follows the
// untouched stock case9/error path and leaves the server pending T1 untouched.
.org RecoveryC_State17SuccessResult
    ldrb r0,[r4,#0x62]

// Keep the stock UI helper, but use the neutral connection/wait message while
// the persist-only repair runs. This text is not used as evidence of server
// lock state.
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

// Entry contract from 0x002A9518:
//   r0 = current GameRecoveryRecord *
//   r4 = current state17 object
//
// Ordinary status1/2: reproduce the stock LDRB and continue unchanged.
// C4 status3: mark this state17 instance result=3, restore persisted status=1,
//             and route directly to case5 so stock game-save start/poll runs
//             before any remote transaction is attempted.
OfficialExistingLock_State17Status:
    ldrb r1,[r0,#0x1c]
    cmp r1,#3
    streqb r1,[r4,#0x62]
    moveq r2,#1
    streqb r2,[r0,#0x1c]
    moveq r0,#5
    beq RecoveryC_State17StoreSubstate
    mov r0,r1
    b RecoveryC_State17StatusResume

.align 2
    .importobj "../build/official_existing_lock_recovery_arm.o"
.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
