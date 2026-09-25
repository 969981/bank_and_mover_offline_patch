.syntax unified
.cpu mpcore
.arm
.text
.align 2

// Recovery C4: repair an already-existing state18 mismatch using only the
// CURRENT server BankTransactionParam.  No WAL/history is consulted and no
// Commit path exists here.
//
// Entry contract at the two genuine state18 game-mismatch edges:
//   r4        = state18 object
//   r0        = current GameRecoveryRecord *
//   [r4+0x28] = current server BankTransactionParam *
//
// C4 rebuilds an exact in-memory GameRecoveryRecord and marks it status=3 only
// as a RAM-only handoff marker.  state17 consumes 3 immediately, restores
// stock status=1, persists the repaired record with the stock game writer, and
// exits the current session WITHOUT a remote transaction.  The next launch is
// therefore ordinary stock recovery against a durable matching record.

.equ State18StoreSubstate, 0x002A8980

.global OfficialExistingLock_GameMismatch
.type OfficialExistingLock_GameMismatch,%function
OfficialExistingLock_GameMismatch:
    cmp r0,#0
    beq .Lstock_mismatch
    ldr r1,[r4,#0x28]
    cmp r1,#0
    beq .Lstock_mismatch

    // server -> GameRecoveryRecord, exact CURRENT T1.
    // Use doubleword transfers to stay inside the verified RX-tail budget.
    ldrd r2,r3,[r1,#0x00]
    strd r2,r3,[r0,#0x00]
    ldrd r2,r3,[r1,#0x18]
    strd r2,r3,[r0,#0x08]
    ldrd r2,r3,[r1,#0x08]
    strd r2,r3,[r0,#0x10]
    ldr r2,[r1,#0x10]
    str r2,[r0,#0x18]

    // 3 is never meant to be persisted. state17 converts it to stock status=1
    // before invoking the stock game-save writer.
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

    // Enter stock state17 without performing state18 Commit/Rollback. C4's
    // state17 hook performs persist-only repair first.
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
