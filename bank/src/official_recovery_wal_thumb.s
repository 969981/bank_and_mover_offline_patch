.syntax unified
.cpu mpcore
.thumb
.text
.align 2

// Recovery A production candidate.  This helper layer reuses stock Bank-local
// recovery as a pre-Stage write-ahead journal (custom status=3); it performs no
// custom SD file I/O and leaves normal stock status 1/2 semantics unchanged.

.thumb_func
.global OfficialRecovery_WalCase1
OfficialRecovery_WalCase1:
    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#8
    beq 1f
    movs r1,#7
    strb r1,[r4,r2]
    movs r0,#7
    ldr r3,=0x002B2174
    bx r3
1:
    movs r1,#0
    strb r1,[r4,r2]
    mov r0,r4
    bx lr

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
    // Restore the flags expected by stock BEQ at 0x002B2098.
    cmp r3,#1
    bx lr

.thumb_func
.global OfficialRecovery_WalLocalStatusA
OfficialRecovery_WalLocalStatusA:
    cmp r0,#3
    bne 9f

    // dataId + curVersion have already matched in stock state18.  Complete the
    // ownership check with updateVersion, size and the 64-bit transactionPassword.
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

    // Exact status=3 WAL -> variant A always uses stock rollback state6.
    movs r0,#6
    b 7f
8:
    // Stale / foreign WAL: discard it for this recovery decision and let stock
    // continue with the game recovery record (state4).
    movs r0,#4
7:
    ldr r3,=0x002A8980
    bx r3
9:
    // For ordinary local status=2, reconstruct the CMP replaced at 0x002A8974.
    cmp r0,#2
    bx lr
