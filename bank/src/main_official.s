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
.definelabel RecoveryA_SaveCase8Result,         0x002B2090

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Existing Official Bulk Sync V3 hook.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// -----------------------------------------------------------------------------
// Recovery A: bulk-only durable pre-RMC52 stock-status1 WAL
// -----------------------------------------------------------------------------
// Replaces stock `mov r0,r4`. For an ordinary save the helper simply restores
// r0=r4. For a Bulk session it first routes through stock case7, which persists
// the exact BankTransactionParam with native status=1 before any RMC52 request.
// On the second pass the helper disarms the transient Bulk flag and returns
// r0=r4, so the untouched BL at 0x002B1DE8 starts SerializeAndStage once.
.org RecoveryA_SaveCase1
    blx OfficialRecovery_WalCase1

// During the private pre-Stage journal pass the helper routes local-save
// success back to case1 and failure to state20. Ordinary case8 returns with the
// original CMP flags expected by stock MOVEQ/BEQ at 0x002B2094/0x002B2098.
.org RecoveryA_SaveCase8Result
    blx OfficialRecovery_WalCase8Result

// No state18 hook is needed in Variant A. The durable record is native
// status=1, so stock state18 already performs exact dataId/curVersion matching
// and selects the native Rollback path.

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
