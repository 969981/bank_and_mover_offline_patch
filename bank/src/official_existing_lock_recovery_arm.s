.syntax unified
.cpu mpcore
.arm
.text
.align 2

// Recovery C: repair an already-existing state18 mismatch using only the
// CURRENT server BankTransactionParam.  No WAL/history is consulted and no
// Commit path exists here.
//
// Entry contract at the two genuine state18 game-mismatch edges:
//   r4        = state18 object
//   r0        = current GameRecoveryRecord *
//   [r4+0x28] = current server BankTransactionParam *
//
// We rebuild the in-memory game recovery record as status=1 and mirror the
// current server transaction into state18's canonical context.  state18 is
// then completed through stock case11/result4 so stock state17 performs the
// single RollbackBankObject call, clears transactionPassword, and saves the
// game through the stock family-specific writer.

.equ State18StoreSubstate, 0x002A8980

.global OfficialExistingLock_GameMismatch
.type OfficialExistingLock_GameMismatch,%function
OfficialExistingLock_GameMismatch:
    cmp r0,#0
    beq .Lstock_mismatch
    ldr r1,[r4,#0x28]
    cmp r1,#0
    beq .Lstock_mismatch

    // server -> GameRecoveryRecord
    // dataId + curVersion
    ldmia r1,{r2,r3,r12}
    stmia r0,{r2,r3}
    str r12,[r0,#0x10]

    // transactionPassword
    ldr r2,[r1,#0x18]
    ldr r3,[r1,#0x1c]
    str r2,[r0,#0x08]
    str r3,[r0,#0x0c]

    // updateVersion + size
    ldr r2,[r1,#0x0c]
    str r2,[r0,#0x14]
    ldr r2,[r1,#0x10]
    str r2,[r0,#0x18]

    // C is rollback-only.  Mark as a synthetic game-source context so the
    // following stock state17 path cannot reinterpret stale status=2 data.
    mov r2,#1
    strb r2,[r0,#0x1c]
    strb r2,[r4,#0x88]

    // Mirror CURRENT SERVER T1 verbatim into state18 canonical tx storage.
    // BankTransactionParam is exactly 0x20 bytes.
    add r3,r4,#0x40
    ldmia r1!,{r2,r12,lr}
    stmia r3!,{r2,r12,lr}
    ldmia r1!,{r2,r12,lr}
    stmia r3!,{r2,r12,lr}
    ldmia r1!,{r2,r12}
    stmia r3!,{r2,r12}

    // Stock state18 case11 sets result=4.  The outer flow then enters state17,
    // which sees the synthetic status=1 record, performs one stock Rollback,
    // clears the password and persists normal game-side cleanup.
    mov r0,#11
    b .Lset_substate

.Lstock_mismatch:
    // Fail closed: preserve the stock Trainer/save mismatch state.
    mov r0,#8

.Lset_substate:
    ldr r3,=State18StoreSubstate
    bx r3
    .ltorg

.size OfficialExistingLock_GameMismatch,.-OfficialExistingLock_GameMismatch
