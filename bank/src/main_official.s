.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official-only bulk sync. Keep every executable byte inside the real RX text
// tail padding. No .data/BSS region is repurposed as code or scratch storage.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Run before the stock state machine consumes its native callback status byte.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// Recovery A deliberately changes only the stock paths that would otherwise
// enter state18 substate 8 (Trainer/save mismatch / invalid recovery status).
// Both funnels are redirected into the now-unreachable stock case8 body, which
// becomes a tiny rollback shim. This consumes no additional RX-tail space.
.org BankRecovery_InvalidStatusFunnel
    b OfficialRecovery_A_RollbackShim

.org BankRecovery_MismatchFunnel
    b OfficialRecovery_A_RollbackShim

// Stock case8 is reachable only from the two substate-8 funnels above in this
// state machine. Variant A replaces its first 0x20 bytes with a raw transaction
// copy and then rejoins stock substate 6 (RollbackBankObject).
.org BankRecovery_ErrorCase8
.area 0x20
OfficialRecovery_A_RollbackShim:
    ldr r0,[r4,#0x28]              // CURRENT server BankTransactionParam*
    add r1,r4,#0x40                // state-owned recovery transaction buffer
    ldmia r0!,{r2,r3,r5-r7,r12}    // first 6 words
    stmia r1!,{r2,r3,r5-r7,r12}
    ldmia r0!,{r2,r3}              // last 2 words
    stmia r1!,{r2,r3}
    mov r0,#6                       // stock state18 case6 = Rollback
    b BankRecovery_SetSubstate
.endarea

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

.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
