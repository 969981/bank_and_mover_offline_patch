.syntax unified
.cpu mpcore
.thumb
.text
.align 2

// Recovery A production WAL.
//
// Variant A is Bulk-only and always prefers rollback after an interrupted
// transaction. Before RMC52, divert once through the stock case7 local-save
// path, which persists the exact BankTransactionParam with native status=1.
// Keep the Bulk session armed through Stage so a later successful game save
// cannot upgrade the local recovery record to status=2; case5 writes status=1
// for Bulk and preserves stock status=2 for ordinary Bank saves.

.equ RecoverySessionFlag, 0x003ABFFC
.equ BankSaveSetSubstate, 0x002B2174

.thumb_func
.global OfficialRecovery_WalCase1
OfficialRecovery_WalCase1:
    ldr r3,=RecoverySessionFlag
    ldrb r1,[r3]
    cmp r1,#1
    bne 2f

    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#8
    beq 1f

    // First pass: send stock state7 through its native status=1 local recovery
    // save before any Stage/RMC52 request can create server pending state.
    movs r1,#7
    strb r1,[r4,r2]
    movs r0,#7
    ldr r3,=BankSaveSetSubstate
    bx r3

1:
    // Second pass after durable status=1 WAL. Clear only the private state byte;
    // keep RecoverySessionFlag armed through Stage/game-save so case5 can force
    // the durable local record to remain rollback-only.
    movs r1,#0
    strb r1,[r4,r2]
2:
    mov r0,r4
    bx lr

.thumb_func
.global OfficialRecovery_WalCase5Status
OfficialRecovery_WalCase5Status:
    // Stock case5 normally writes status=2 after game-save success. For the
    // Bulk transaction keep status=1, then disarm the transient session flag.
    // Ordinary Bank sessions retain the original status=2 behavior.
    ldr r3,=RecoverySessionFlag
    ldrb r1,[r3]
    cmp r1,#1
    bne 1f
    movs r1,#0
    strb r1,[r3]
    movs r1,#1
    bx lr
1:
    movs r1,#2
    bx lr

.thumb_func
.global OfficialRecovery_WalCase8Result
OfficialRecovery_WalCase8Result:
    // Used at stock case8's `cmp r0,#1`. Only the pre-Stage journal pass is
    // intercepted. On a later game-save failure the ordinary case7/case8 path
    // also reaches here; clear a still-armed Bulk flag before returning stock
    // CMP flags so a subsequent save in the same process cannot inherit it.
    mov r3,r0
    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#7
    bne 3f
    cmp r3,#1
    bne 2f

    // WAL persisted: return to case1; Stage starts on the second pass.
    movs r1,#8
    strb r1,[r4,r2]
    movs r0,#1
    ldr r3,=BankSaveSetSubstate
    bx r3
2:
    // Could not persist the rollback WAL: never start the remote transaction.
    movs r1,#0
    strb r1,[r4,r2]
    ldr r3,=RecoverySessionFlag
    strb r1,[r3]
    movs r0,#20
    ldr r3,=BankSaveSetSubstate
    bx r3
3:
    // Ordinary case8 / post-Stage rollback save: disarm any surviving Bulk flag
    // and reconstruct stock CMP flags for MOVEQ/BEQ at 0x2B2094/0x2B2098.
    ldr r2,=RecoverySessionFlag
    movs r1,#0
    strb r1,[r2]
    cmp r3,#1
    bx lr
