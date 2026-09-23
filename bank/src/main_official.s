.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official-only bulk sync. Keep every executable byte inside the real RX text
// tail padding. No .data/BSS region is repurposed as code or scratch storage.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

// Recovery A save-state landmarks verified against Bank v1.5.
.definelabel RecoveryA_SaveCase1,          0x002B1DE4
.definelabel RecoveryA_SaveCase5Status,    0x002B1F50
.definelabel RecoveryA_SaveCase7,          0x002B1FF8
.definelabel RecoveryA_SaveCase8Result,    0x002B2090
.definelabel RecoveryA_SaveSetSubstate,    0x002B2174

// Private transient markers stored in state+0x48 only before RMC52 starts.
// The byte is cleared immediately before BankSave_SerializeAndStage, so stock
// remote callbacks keep their native 0/1 semantics afterwards.
.definelabel RecoveryA_JournalSaving,       7
.definelabel RecoveryA_JournalReady,        8

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Existing Official Bulk Sync V3 hook.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// -----------------------------------------------------------------------------
// Recovery A: durable rollback journal for every unresolved remote transaction
// -----------------------------------------------------------------------------
// Before the first remote Stage/Prepare request, persist the exact current
// BankTransactionParam into the stock Bank-local RecoveryRecord with status=1.
// This closes the earliest window where the server can have a pending tx while
// neither game nor local recovery state is durable.
.org RecoveryA_SaveCase1
    b OfficialRecovery_A_PreStageJournal

// After game save succeeds, stock case5 normally upgrades the local record to
// status=2. Variant A deliberately keeps status=1 until remote Complete really
// succeeds. Therefore any restart with an unresolved server transaction chooses
// stock Rollback, even if game save itself had already succeeded.
.org RecoveryA_SaveCase5Status
    mov r1,#1

// Reuse stock case7/case8 for the pre-Stage local journal persistence.
.org RecoveryA_SaveCase8Result
    b OfficialRecovery_A_AfterJournalPersist

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

OfficialRecovery_A_PreStageJournal:
    ldrb r1,[r4,#0x48]
    cmp r1,#RecoveryA_JournalReady
    beq @@stage
    mov r1,#RecoveryA_JournalSaving
    strb r1,[r4,#0x48]
    mov r0,#7
    b RecoveryA_SaveSetSubstate
@@stage:
    mov r1,#0
    strb r1,[r4,#0x48]
    mov r0,r4
    bl BankSave_SerializeAndStage
    b RecoveryA_SaveCase1 + 8

OfficialRecovery_A_AfterJournalPersist:
    ldrb r1,[r4,#0x48]
    cmp r1,#RecoveryA_JournalSaving
    bne @@stockCase8
    cmp r0,#1
    bne @@journalFailed
    mov r1,#RecoveryA_JournalReady
    strb r1,[r4,#0x48]
    mov r0,#1
    b RecoveryA_SaveSetSubstate
@@journalFailed:
    mov r1,#0
    strb r1,[r4,#0x48]
    mov r0,#20
    b RecoveryA_SaveSetSubstate
@@stockCase8:
    cmp r0,#1
    b RecoveryA_SaveCase8Result + 4

.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
