.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official-only bulk sync. Keep every executable byte inside the real RX text
// tail padding. No .data/BSS region is repurposed as code or scratch storage.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

// Recovery B save-state landmarks verified against Bank v1.5.
.definelabel RecoveryB_SaveCase1,               0x002B1DE4
.definelabel RecoveryB_SaveCase7,               0x002B1FF8
.definelabel RecoveryB_SaveCase8Result,         0x002B2090
.definelabel RecoveryB_SaveSetSubstate,         0x002B2174

// Recovery B state18 landmarks.
.definelabel RecoveryB_LocalDataIdMismatch,     0x002A8904
.definelabel RecoveryB_LocalVersionMismatch,    0x002A891C
.definelabel RecoveryB_LocalStatusDecision,     0x002A8968
.definelabel RecoveryB_LocalMismatchClear,      0x002A8980
.definelabel RecoveryB_GameCheckEntry,          0x002A8988
.definelabel RecoveryB_GameDataIdMismatch,      0x002A89D0
.definelabel RecoveryB_GameVersionMismatch,     0x002A89E0
.definelabel RecoveryB_State18SetSubstate,      0x002A8980
.definelabel RecoveryB_State18Commit,            0x002A8AC8

// Private transient markers used only before RMC52 starts.
.definelabel RecoveryB_JournalSaving,            7
.definelabel RecoveryB_JournalReady,             8

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Existing Official Bulk Sync V3 hook.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// -----------------------------------------------------------------------------
// Recovery B: pre-RMC52 write-ahead rollback journal
// -----------------------------------------------------------------------------
// Persist the exact current BankTransactionParam as a stock local status=1
// recovery record before the server can create the pending transaction.
.org RecoveryB_SaveCase1
    b OfficialRecovery_B_PreStageJournal

.org RecoveryB_SaveCase8Result
    b OfficialRecovery_B_AfterJournalPersist

// -----------------------------------------------------------------------------
// Recovery B: smart state18 decision
// -----------------------------------------------------------------------------
// If the local record does not exactly match the CURRENT server transaction,
// clear the private "local rollback journal verified" flag and inspect the game
// record exactly as stock does.
.org RecoveryB_LocalDataIdMismatch
    b RecoveryB_LocalMismatchClear
.org RecoveryB_LocalVersionMismatch
    b RecoveryB_LocalMismatchClear

// Replace only the 0x20-byte local-status decision block.  An exact status=1
// local record is our durable rollback fallback, but B first inspects the game
// recovery record: exact game status=2 is stronger evidence that game save was
// committed and therefore keeps the stock Commit path.  Exact local status=2
// remains a direct stock Commit.
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

// Hook only the two real game transaction mismatch branches.  Never hook the
// shared state=8 funnel.  If an exact local status=1 journal was verified, a
// game mismatch means game save was not proven durable -> stock Rollback.
// Otherwise preserve stock mismatch behavior.
.org RecoveryB_GameDataIdMismatch
    bne OfficialRecovery_B_GameMismatchDecision
.org RecoveryB_GameVersionMismatch
    bne OfficialRecovery_B_GameMismatchDecision

.org OfficialBulk_CodeStart
.area OfficialBulk_CodeEnd-OfficialBulk_CodeStart
.arm

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

// Same durable pre-Stage journal used by Variant A.
OfficialRecovery_B_PreStageJournal:
    ldrb r1,[r4,#0x48]
    cmp r1,#RecoveryB_JournalReady
    beq @@stage
    mov r1,#RecoveryB_JournalSaving
    strb r1,[r4,#0x48]
    mov r0,#7
    b RecoveryB_SaveSetSubstate
@@stage:
    mov r1,#0
    strb r1,[r4,#0x48]
    mov r0,r4
    bl BankSave_SerializeAndStage
    b RecoveryB_SaveCase1 + 8

OfficialRecovery_B_AfterJournalPersist:
    ldrb r1,[r4,#0x48]
    cmp r1,#RecoveryB_JournalSaving
    bne @@stockCase8
    cmp r0,#1
    bne @@journalFailed
    mov r1,#RecoveryB_JournalReady
    strb r1,[r4,#0x48]
    mov r0,#1
    b RecoveryB_SaveSetSubstate
@@journalFailed:
    mov r1,#0
    strb r1,[r4,#0x48]
    mov r0,#20
    b RecoveryB_SaveSetSubstate
@@stockCase8:
    cmp r0,#1
    b RecoveryB_SaveCase8Result + 4

// Called only from the two exact game mismatch BNEs.  state+0x88==2 is set
// only after the immediately preceding local record exactly matched server
// dataId/curVersion and carried status=1.  state+0x40 already contains that
// exact local transaction, so case6 can use the stock Rollback routine.
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
