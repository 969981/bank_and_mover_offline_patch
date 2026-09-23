.syntax unified
.cpu mpcore
.thumb
.text
.align 2

// Recovery A production WAL.  Only a session in which Official Bulk Sync
// actually applied data may create the private status=3 write-ahead record.
// The exact transaction is persisted through the stock Bank-local save path
// before RMC52 can create the server-side pending transaction.

.equ RecoverySessionFlag, 0x003ABFFC
.equ BankSaveSerializeAndStage, 0x002B2320
.equ BankSaveSetSubstate, 0x002B2174
.equ State18StoreSubstate, 0x002A8980

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

    movs r1,#7
    strb r1,[r4,r2]
    movs r0,#7
    ldr r3,=BankSaveSetSubstate
    bx r3

1:
    // Durable status=3 WAL exists.  Disarm before the real Stage call; later
    // stock case7 failures must keep their native status=1 semantics.
    movs r1,#0
    strb r1,[r4,r2]
    ldr r3,=RecoverySessionFlag
    strb r1,[r3]
2:
    mov r0,r4
    ldr r3,=BankSaveSerializeAndStage
    bx r3

.thumb_func
.global OfficialRecovery_WalSelectStatus
OfficialRecovery_WalSelectStatus:
    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#7
    bne 1f
    movs r1,#3
    bx lr
1:
    movs r1,#1
    bx lr

.thumb_func
.global OfficialRecovery_WalCase8Result
OfficialRecovery_WalCase8Result:
    mov r3,r0
    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#7
    bne 1f
    cmp r3,#1
    bne 2f
    movs r1,#8
    strb r1,[r4,r2]
    movs r0,#1
    b 2f
1:
    cmp r3,#1
    bne 2f
    movs r0,#11
2:
    // Restore the flags expected by the stock BEQ at 0x002B2098.
    cmp r3,#1
    bx lr

.thumb_func
.global OfficialRecovery_WalLocalStatusA
OfficialRecovery_WalLocalStatusA:
    cmp r0,#3
    bne 9f

    // dataId + curVersion already matched in stock state18.  Complete ownership
    // validation with updateVersion, size and the 64-bit transactionPassword.
    ldr r1,[r4,#0x28]
    ldr r2,[r4,#0x4c]
    ldr r3,[r1,#0x0c]
    eors r2,r3
    ldr r3,[r4,#0x50]
    ldr r0,[r1,#0x10]
    eors r3,r0
    orrs r2,r3
    ldr r3,[r4,#0x58]
    ldr r0,[r1,#0x18]
    eors r3,r0
    orrs r2,r3
    ldr r3,[r4,#0x5c]
    ldr r0,[r1,#0x1c]
    eors r3,r0
    orrs r2,r3
    bne 8f

    // Variant A: an exact private WAL is always the safe rollback fallback.
    movs r0,#6
    b 7f
8:
    // Stale/foreign status=3 data is never trusted.
    movs r0,#4
7:
    ldr r3,=State18StoreSubstate
    bx r3
9:
    // Reconstruct the stock CMP replaced at 0x002A8974.
    cmp r0,#2
    bx lr
