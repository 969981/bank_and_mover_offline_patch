.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official Bulk Sync + recovery-A transaction hardening. Every added
// executable byte remains inside the verified RX text tail; hook sites only
// replace instructions verified against the exact Bank v1.5 image.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

.definelabel RecoveryA_SaveCase1,               0x002B1DE4
.definelabel RecoveryA_SaveCase7Status,         0x002B1FFC
.definelabel RecoveryA_SaveCase8Result,         0x002B2090
.definelabel RecoveryA_LocalStatusCmp2,          0x002A8974

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Existing Official Bulk Sync V3 hook.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// -----------------------------------------------------------------------------
// Recovery A: bulk-only durable pre-RMC52 WAL
// -----------------------------------------------------------------------------
// Replaces stock `mov r0,r4`. The helper returns r0=r4 for ordinary saves and
// for the second journal pass, so the untouched BL at 0x002B1DE8 starts the
// native SerializeAndStage call exactly once.
.org RecoveryA_SaveCase1
    blx OfficialRecovery_WalCase1

// Stock case7 writes status=1. Only the private pre-Stage journal pass selects
// status=3; ordinary game-save rollback records stay native status=1.
.org RecoveryA_SaveCase7Status
    blx OfficialRecovery_WalSelectStatus

// During the private journal pass the helper routes success back to case1 and
// failure to state20. Ordinary case8 returns with stock CMP flags intact.
.org RecoveryA_SaveCase8Result
    blx OfficialRecovery_WalCase8Result

// Stock already handled local status=1 before this instruction. Replace only
// the status=2 CMP: private status=3 performs the full ownership check and, if
// exact, selects stock Rollback state6. Ordinary status=2 returns with EQ set.
.org RecoveryA_LocalStatusCmp2
    blx OfficialRecovery_WalLocalStatusA

// -----------------------------------------------------------------------------
// RX-tail payload
// -----------------------------------------------------------------------------
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

.align 2
    .importobj "../build/official_recovery_wal_thumb.o"
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
