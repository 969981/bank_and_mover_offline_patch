.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official Bulk Sync + Recovery C (Existing Lock Recovery).
// Keep every executable byte inside the verified RX text tail. Recovery C
// replaces only narrow, machine-code-verified recovery/state-routing points.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

.definelabel RecoveryC_GameDataIdMismatch,      0x002A89D0
.definelabel RecoveryC_GameVersionMismatch,     0x002A89E0
.definelabel RecoveryC_State17CtorMarkerInit,   0x002A61C8
.definelabel RecoveryC_State17StatusLoad,       0x002A9518
.definelabel RecoveryC_State17StatusResume,     0x002A951C
.definelabel RecoveryC_State17SuccessResult,    0x002A966C
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

// state17 allocates 0x68 bytes and stock owns +0x60/+0x61 for callback status.
// +0x62 is unused by stock state17.  Initialize the dword at +0x60 as
// 00 00 04 00 so ordinary state17 success still returns result=4 while keeping
// both stock callback bytes cleared.  Recovery C changes only +0x62 to 3.
.org RecoveryC_State17CtorMarkerInit
    mov r1,#0x40000
    str r1,[r0,#0x60]

// Consume Recovery C's transient GameRecoveryRecord.status=3 before stock
// state17 evaluates status.  The helper restores the record to stock status=1
// before any persistence and marks this state17 instance to disconnect after
// successful Rollback + cleanup instead of immediately entering state16.
.org RecoveryC_State17StatusLoad
    b OfficialExistingLock_State17Status

// Stock case7 is the successful terminal result.  For ordinary state17 +0x62
// is 4, reproducing stock behavior exactly.  Recovery C sets it to 3, and the
// existing STRB/MOV/POP sequence then returns result=3 -> state20 cleanup.
.org RecoveryC_State17SuccessResult
    ldrb r0,[r4,#0x62]

// Keep the stock UI helper, but use the neutral connection/wait message while
// state17 performs the recovery operation.  This avoids presenting the fixed
// stock "server locked" banner before Rollback has even been attempted.
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
// status 1/2: reproduce the stock LDRB and continue unchanged.
// status 3: Recovery C marker.  Record result=3 in state17-local +0x62, restore
//           the GameRecoveryRecord to stock Rollback status=1, and then let the
//           stock CMP/MOVEQ path choose substate3 Rollback.
OfficialExistingLock_State17Status:
    ldrb r1,[r0,#0x1c]
    cmp r1,#3
    strbeq r1,[r4,#0x62]
    moveq r1,#1
    strbeq r1,[r0,#0x1c]
    mov r0,r1
    b RecoveryC_State17StatusResume

.align 2
    .importobj "../build/official_existing_lock_recovery_arm.o"
.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
