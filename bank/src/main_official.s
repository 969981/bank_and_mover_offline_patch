.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official-only bulk sync. Keep every executable byte inside the real RX text
// tail padding. No .data/BSS region is repurposed as code or scratch storage.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

// Verified BankSaveState_Update / state18 landmarks for Recovery B.
.definelabel RecoveryB_SaveCase2Success,       0x002B1E08
.definelabel RecoveryB_SaveCase8Result,        0x002B2090
.definelabel RecoveryB_SaveSetSubstate,        0x002B2174
.definelabel RecoveryB_LocalDataIdMismatch,    0x002A8904
.definelabel RecoveryB_LocalVersionMismatch,   0x002A891C
.definelabel RecoveryB_LocalStatusDecision,    0x002A8968
.definelabel RecoveryB_GameCheckEntry,         0x002A8988
.definelabel RecoveryB_LocalMismatchClear,     0x002A8980
.definelabel RecoveryB_GameMismatchFunnel,     0x002A8AD0
.definelabel RecoveryB_State18SetSubstate,      0x002A8980
.definelabel RecoveryB_State18Commit,           0x002A8AC8

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Existing V3 bulk hook.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// -----------------------------------------------------------------------------
// Recovery B: stock-record write-ahead journal
// -----------------------------------------------------------------------------
// After Stage/Prepare succeeds, do NOT start game save immediately. First route
// through stock case7/case8 to persist an exact local status=1 rollback record.
// state+0x48 is free between the consumed Stage callback and the later remote
// Complete/Rollback callbacks; value 7 marks this one pre-journal pass.
.org RecoveryB_SaveCase2Success
    mov r1,#7
    strb r1,[r4,#0x48]
    // stock instructions at +8 continue with:
    //   str r1,[r4,#0x10]   ; substate 7
    //   b   function end

// case8 is reached after the local status=1 journal persistence completes.
// r0==0 was already handled by the stock wait branch at 0x002B208C; every
// non-zero result comes here. The tail shim distinguishes the pre-journal pass
// from the normal game-save-failure use of case7/case8.
.org RecoveryB_SaveCase8Result
    b OfficialRecovery_B_AfterLocalJournalPersist

// In state18, a local exact status=1 record is now a write-ahead journal rather
// than an immediate Rollback verdict. Check the game record first:
//   exact game status=2 -> stock Commit
//   game mismatch       -> Rollback local journal
// Local mismatch/invalid status clears the journal flag and falls through to
// the ordinary game-record check.
.org RecoveryB_LocalDataIdMismatch
    b RecoveryB_LocalMismatchClear
.org RecoveryB_LocalVersionMismatch
    b RecoveryB_LocalMismatchClear

.org RecoveryB_LocalStatusDecision
.area 0x20
    cmp r0,#1
    moveq r1,#2
    streqb r1,[r4,#0x88]
    beq RecoveryB_GameCheckEntry
    cmp r0,#2
    beq RecoveryB_State18Commit
RecoveryB_LocalMismatchClear:
    mov r1,#0
    strb r1,[r4,#0x88]
.endarea

// The stock game-dataId and game-curVersion mismatch branches both converge
// here. If +0x88==2, an exact local rollback journal was already verified and
// copied to state+0x40, so use stock case6. Otherwise preserve stock substate8.
.org RecoveryB_GameMismatchFunnel
    b OfficialRecovery_B_GameMismatchDecision

.org OfficialBulk_CodeStart
.area OfficialBulk_CodeEnd-OfficialBulk_CodeStart
.arm

// Existing V3 dispatch.
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

// BankSave case8 completion shim.  The pre-journal pass clears its private
// state+0x48 marker and advances to stock case3 only after local persistence
// succeeded. If that persistence failed, immediately route to stock case11
// Rollback instead of starting the game save.
OfficialRecovery_B_AfterLocalJournalPersist:
    ldrb r1,[r4,#0x48]
    cmp r1,#7
    bne @@stockCase8
    mov r1,#0
    strb r1,[r4,#0x48]
    cmp r0,#1
    moveq r0,#3
    movne r0,#11
    b RecoveryB_SaveSetSubstate
@@stockCase8:
    cmp r0,#1
    b 0x002B2094

// state18 game mismatch decision. state+0x88==2 only when the immediately
// preceding local recovery record exactly matched the CURRENT server tx and
// had status=1. Its transaction fields are already in state+0x40.
OfficialRecovery_B_GameMismatchDecision:
    ldrb r0,[r4,#0x88]
    cmp r0,#2
    moveq r0,#6
    movne r0,#8
    b RecoveryB_State18SetSubstate

.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
