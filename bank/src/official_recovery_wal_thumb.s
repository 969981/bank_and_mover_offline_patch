.syntax unified
.cpu mpcore
.thumb
.text
.align 2

// Recovery B production WAL.
//
// A private status=3 Bank-local recovery record is persisted before RMC52,
// but only when the current process has actually applied bulk_import.bin.
// On recovery, an exact status=3 WAL validates every transaction field and
// asks stock state4 to inspect the game record.  A valid game status=2 can
// Commit; game mismatch falls back to Rollback via the in-place ARM decision
// block at 0x002A8A64.

.equ OFFICIAL_BULK_SESSION_FLAG, 0x003ABFFC
.equ BANK_SAVE_SET_SUBSTATE,     0x002B2174
.equ RECOVERY_SET_SUBSTATE,      0x002A8980

.thumb_func
.global OfficialRecovery_WalCase1
OfficialRecovery_WalCase1:
    // Normal Bank sessions must remain completely stock.
    ldr r3,=OFFICIAL_BULK_SESSION_FLAG
    ldrb r3,[r3]
    cmp r3,#1
    bne 2f

    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#8
    beq 1f
    movs r1,#7
    strb r1,[r4,r2]
    movs r0,#7
    ldr r3,=BANK_SAVE_SET_SUBSTATE
    bx r3
1:
    // The exact tx is now durable as status=3; allow stock case1 to Stage it.
    movs r1,#0
    strb r1,[r4,r2]
2:
    mov r0,r4
    bx lr

.thumb_func
.global OfficialRecovery_WalSelectStatus
OfficialRecovery_WalSelectStatus:
    // Used at stock case7's `mov r1,#1`.  Only the private journal pass uses 3;
    // ordinary rollback saves keep the native status=1 meaning.
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
    // Used at stock case8's `cmp r0,#1`.
    mov r3,r0
    movs r2,#0x48
    ldrb r1,[r4,r2]
    cmp r1,#7
    bne 3f

    // This was the pre-Stage WAL save, not a normal rollback save.  Do not let
    // the stock MOVEQ at 0x002B2094 send us to state11.
    cmp r3,#1
    bne 2f
    movs r1,#8
    strb r1,[r4,r2]
    movs r0,#1
    b 1f
2:
    movs r1,#0
    strb r1,[r4,r2]
    movs r0,#20
1:
    ldr r3,=BANK_SAVE_SET_SUBSTATE
    bx r3
3:
    // Ordinary case8: restore exactly the flags expected by stock MOVEQ/BEQ.
    cmp r3,#1
    bx lr

.thumb_func
.global OfficialRecovery_WalLocalStatusB
OfficialRecovery_WalLocalStatusB:
    // This helper replaces the stock local-status decision and always routes
    // directly through the stock state setter; it never returns to the patched
    // ARM instruction.
    cmp r0,#3
    bne 4f

    // dataId + curVersion have already matched in stock state18.  Complete the
    // ownership check with updateVersion, size and transactionPassword.
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

    // Exact private WAL.  Mark that a trusted rollback fallback exists, then
    // let stock state4 validate the game recovery record.
    movs r2,#0x88
    movs r0,#2
    strb r0,[r4,r2]
    movs r0,#4
    b 7f
3:
    // Stale/foreign status=3 record: never use it for remote recovery.
    movs r0,#4
    b 7f
4:
    // Preserve stock status 1/2 meanings for non-WAL records.
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
    ldr r3,=RECOVERY_SET_SUBSTATE
    bx r3
