.syntax unified
.cpu mpcore
.thumb
.text
.align 2

// Recovery B production WAL. Only a session in which Official Bulk Sync
// actually applied data may create the private status=3 write-ahead record.
// The WAL is persisted through the stock Bank-local save path before RMC52.

.equ RecoverySessionFlag, 0x003ABFFC
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
    // Durable status=3 WAL exists. Disarm before the untouched stock BL at
    // 0x002B1DE8 starts the real SerializeAndStage call.
    movs r1,#0
    strb r1,[r4,r2]
    ldr r3,=RecoverySessionFlag
    strb r1,[r3]
2:
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
    bne 3f
    cmp r3,#1
    bne 2f
    movs r1,#8
    strb r1,[r4,r2]
    movs r0,#1
    ldr r3,=BankSaveSetSubstate
    bx r3
2:
    movs r1,#0
    strb r1,[r4,r2]
    movs r0,#20
    ldr r3,=BankSaveSetSubstate
    bx r3
3:
    cmp r3,#1
    bx lr

.thumb_func
.global OfficialRecovery_WalLocalStatusB
OfficialRecovery_WalLocalStatusB:
    cmp r0,#3
    bne 4f

    // dataId + curVersion already matched in stock state18. Complete ownership
    // validation with updateVersion, size and transactionPassword.
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
    bne 3f

    // Exact WAL: remember a trusted rollback fallback exists, then let stock
    // state4 inspect the game recovery record for possible Commit evidence.
    movs r2,#0x88
    movs r0,#2
    strb r0,[r4,r2]
    movs r0,#4
    b 7f
3:
    // Stale/foreign private WAL cannot authorize a remote operation.
    movs r0,#4
    b 7f
4:
    // Preserve stock status 1/2 meanings for ordinary records.
    cmp r0,#1
    beq 5f
    cmp r0,#2
    beq 6f
    movs r0,#4
    b 7f
5:
    movs r0,#6
    b 7f
6:
    movs r0,#5
7:
    ldr r3,=State18StoreSubstate
    bx r3

.thumb_func
.global OfficialRecovery_WalGameFallbackB
OfficialRecovery_WalGameFallbackB:
    movs r2,#0x88
    ldrb r0,[r4,r2]
    cmp r0,#2
    bne 1f
    movs r0,#6
    bx lr
1:
    movs r0,#8
    bx lr
