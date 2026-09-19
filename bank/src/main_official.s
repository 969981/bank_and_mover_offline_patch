.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official-only Route A bulk sync. The stock title/menu/network/save/HOME flow
// remains untouched. We only mark a successful ordinary Bank download and
// consume that mark on the following BankDataSync update.
.definelabel OfficialBulk_RuntimeStart, 0x00313910
.definelabel OfficialBulk_RuntimeEnd,   0x00314008
.definelabel OfficialBulk_CoreStart,    0x003ABA90
.definelabel OfficialBulk_CoreEnd,      0x003ABFFC
.definelabel OfficialBulk_Scratch,      0x003ABFFC

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

.org BankRemote_DownloadSuccessCallback + 0x14
    bl OfficialBulk_DownloadMarkerTrampoline

.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

.org OfficialBulk_RuntimeStart
.area OfficialBulk_RuntimeEnd-OfficialBulk_RuntimeStart

// Callback +0x14 originally loads r8 with the complete serialized-object size.
// Preserve flags and registers, mark only the ordinary game-linked download
// ([r4+0x41] == 0), then replay that overwritten instruction.
OfficialBulk_DownloadMarkerTrampoline:
    push {r0-r3,r12,lr}
    sub sp,sp,#8
    mrs r12,cpsr
    str r12,[sp]
    ldrb r0,[r4,#0x41]
    cmp r0,#0
    bne @@restoreMarker
    ldr r1,=OfficialBulk_Scratch
    mov r0,#1
    strb r0,[r1]
@@restoreMarker:
    ldr r12,[sp]
    msr cpsr_f,r12
    add sp,sp,#8
    pop {r0-r3,r12,lr}
    ldr r8,=0x000BB528
    bx lr
    .pool

// Replay the native BankDataSyncState_Update prologue. When the ordinary
// download marker is set, consume it once, synchronously snapshot the fresh
// server BankObject, apply bulk_import.bin if valid, then continue native state
// processing in the same frame.
OfficialBulk_BankDataSyncDispatch:
    push {r4-r6,lr}
    mov r4,r0
    ldr r5,=OfficialBulk_Scratch
    ldrb r6,[r5]
    cmp r6,#0
    beq @@native
    mov r6,#0
    strb r6,[r5]
    mov r0,r4
    bl OfficialBulkSync_Process
    mov r0,r4
@@native:
    b BankDataSyncState_Update + 4
    .pool

    .importobj "../build/official_bulk_sync.o"
.endarea

.org OfficialBulk_CoreStart
.area OfficialBulk_CoreEnd-OfficialBulk_CoreStart
    .importobj "../build/official_bulk_sync_core.o"
.endarea

.close
