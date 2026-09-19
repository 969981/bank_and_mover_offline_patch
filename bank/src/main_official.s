.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official-only bulk sync. Keep every executable byte inside the real RX text
// tail padding. No .data/BSS region is repurposed as code or scratch storage.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// State 16/28 complete Bank download hook.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// State 29 HOME pre-migration gate. Stock substate 0 still initializes its
// remote job. Once stock advances to substate 1, the Thumb runtime replaces
// the native rollback with Stage -> CompleteUpdate (or Rollback on failure).
.org HomeRollbackState_Update
    b OfficialBulk_HomeCommitDispatch

.org OfficialBulk_CodeStart
.area OfficialBulk_CodeEnd-OfficialBulk_CodeStart
.arm

// Fetch TLS/FS command buffer in ARM state. Do not introduce imported
// Thumb->ARM R_ARM_THM_CALL relocations: armips relocates those two bytes early
// on this payload.
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

// Return 0 from the runtime to replay the stock State29 function from +4.
// Return nonzero when the custom asynchronous commit gate consumed the frame.
OfficialBulk_HomeCommitDispatch:
    push {r4-r6,lr}
    mov r4,r0
    ldr r12,=OfficialBulkHomeCommit_Process+1
    blx r12
    cmp r0,#0
    bne @@handled
    mov r0,r4
    b HomeRollbackState_Update + 4
@@handled:
    mov r0,#0
    pop {r4-r6,pc}
    .pool

.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
