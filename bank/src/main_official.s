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
.definelabel RecoveryB_GameCheckEntry,          0x002A8988
.definelabel RecoveryB_GameDataIdMismatch,      0x002A89D0
.definelabel RecoveryB_GameVersionMismatch,     0x002A89E0
.definelabel RecoveryB_State18Commit,            0x002A8AC8
.definelabel RecoveryB_State18CommonTail,        0x002A8CD8

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
// Local mismatch must NOT inherit a previous +0x88 journal flag.  Clear it in
// tail code and resume the stock game-record check.
.org RecoveryB_LocalDataIdMismatch
    bne OfficialRecovery_B_LocalMismatchClear
.org RecoveryB_LocalVersionMismatch
    bne OfficialRecovery_B_LocalMismatchClear

// Replace the original 0x20-byte local-status decision block.  Exact local
// status=1 becomes a durable Rollback fallback, but B first inspects the game
// record.  Exact local status=2 remains a direct Commit.  Invalid local status
// clears the private flag and falls through to the stock game check.
.org RecoveryB_LocalStatusDecision
.area 0x20
    cmp r0,#1
    bne @@notRollbackJournal
    mov r1,#2
    strb r1,[r4,#0x88]
    b RecoveryB_GameCheckEntry
@@notRollbackJournal:
    cmp r0,#2
    beq RecoveryB_State18Commit
    b OfficialRecovery_B_LocalMismatchClear
.endarea

// Hook only the two real game transaction mismatch branches.  If an exact
// local status=1 journal was verified, game mismatch means there is no durable
// game status=2 evidence, so use stock Rollback.  Without that exact local
// fallback, preserve stock substate8/Trainer-save mismatch behavior.
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

// Local dataId/version mismatch or invalid local status.  Clear the private
// journal-source flag and resume stock game recovery validation.
OfficialRecovery_B_LocalMismatchClear:
    mov r1,#0
    strb r1,[r4,#0x88]
    b RecoveryB_GameCheckEntry

// Called only from the two exact game mismatch BNEs.  state+0x88==2 is set
// only after the immediately preceding local record exactly matched server
// dataId/curVersion and carried status=1.  state+0x40 already contains that
// exact local transaction.
OfficialRecovery_B_GameMismatchDecision:
    ldrb r0,[r4,#0x88]
    cmp r0,#2
    moveq r0,#6
    movne r0,#8
    str r0,[r4,#0x10]
    b RecoveryB_State18CommonTail

.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
