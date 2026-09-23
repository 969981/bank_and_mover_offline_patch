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

.definelabel RecoveryA_JournalSaving,       7
.definelabel RecoveryA_JournalReady,        8

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// Pre-RMC52 durable rollback journal.
.org RecoveryA_SaveCase1
    b OfficialRecovery_A_PreStageJournal

// Keep local recovery rollback-only even after the game save succeeds.
.org RecoveryA_SaveCase5Status
    mov r1,#1

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

// First pass: route through stock case7/case8 and durably store exact tx as
// status=1. Second pass: clear the private marker before starting RMC52.
OfficialRecovery_A_PreStageJournal:
    ldrb r1,[r4,#0x48]
    cmp r1,#RecoveryA_JournalReady
    movne r1,#RecoveryA_JournalSaving
    strneb r1,[r4,#0x48]
    movne r0,#7
    bne RecoveryA_SaveSetSubstate
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
    moveq r1,#RecoveryA_JournalReady
    movne r1,#0
    strb r1,[r4,#0x48]
    moveq r0,#1
    movne r0,#20
    b RecoveryA_SaveSetSubstate
@@stockCase8:
    cmp r0,#1
    b RecoveryA_SaveCase8Result + 4

.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
