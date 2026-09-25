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
// We rebuild the in-memory game recovery record with transient status=3 and
// mirror the current server transaction into state18's canonical context.
// status=3 is never intended to reach disk: the state17 hook consumes it,
// restores stock rollback status=1, and records a state17-local result marker.
// state17 then performs the single stock RollbackBankObject call, clears
// transactionPassword and saves the game through the stock family writer.

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

    // 3 is Recovery-C-only.  For state18 source selection any non-zero value
    // retains the stock "game source" behavior, while state17 can distinguish
    // this synthetic record from ordinary persisted status=1 Rollback records.
    mov r2,#3
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

    // Stock state18 case11 sets result=4.  The outer flow then enters state17.
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
