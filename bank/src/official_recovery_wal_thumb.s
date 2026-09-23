.syntax unified
.cpu mpcore
.thumb
.text
.align 2

// Recovery A production WAL.
//
// Variant A is Bulk-only and always prefers rollback after an interrupted
// transaction. Therefore no private recovery status is needed: before RMC52,
// divert once through the stock case7 local-save path, which persists the exact
// BankTransactionParam with native status=1. Stock state18 already understands
// an exact status=1 record and will Rollback it without any recovery hook.

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
    // Second pass after durable status=1 WAL. r3 still points at the transient
    // BulkSessionFlag loaded at function entry, so disarm it before Stage.
    movs r1,#0
    strb r1,[r4,r2]
    strb r1,[r3]
2:
    mov r0,r4
    bx lr

.thumb_func
.global OfficialRecovery_WalCase8Result
OfficialRecovery_WalCase8Result:
    // Used at stock case8's `cmp r0,#1`. Only the pre-Stage journal pass is
    // intercepted; ordinary case7 rollback saves keep the native case8 path.
    mov r3,r0
    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#7
    bne 3f
    cmp r3,#1
    bne 2f

    // WAL persisted: return to case1, where the flag is cleared and Stage starts.
    movs r1,#8
    strb r1,[r4,r2]
    movs r0,#1
    ldr r3,=BankSaveSetSubstate
    bx r3
2:
    // Could not persist the rollback WAL: never start the remote transaction.
    movs r1,#0
    strb r1,[r4,r2]
    movs r0,#20
    ldr r3,=BankSaveSetSubstate
    bx r3
3:
    // Ordinary case8: reconstruct stock CMP flags for MOVEQ/BEQ at 0x2B2094.
    cmp r3,#1
    bx lr
