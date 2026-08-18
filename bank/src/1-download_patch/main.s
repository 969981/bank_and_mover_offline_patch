.3ds
.arm
.relativeinclude on

.include "../../include/symbol.inc"

.definelabel DownloadPatch_HookAddress, BankRemote_DownloadSuccessCallback + 0x14
.definelabel DownloadPatch_CodeCaveStart, 0x00313910
.definelabel DownloadPatch_PayloadStart, 0x00313990
.definelabel DownloadPatch_CodeCaveEnd, 0x00314000

.open "../../00040000000C9B00.code", "../../build/1-download_patch/00040000000C9B00.code", 0x00100000

// r7 already contains the successful download's complete bankdata pointer.
// Replace the original ldr r8,[pc,#0x14c] and reproduce it in the trampoline.
.org DownloadPatch_HookAddress
    bl DownloadPatch_Trampoline

.org DownloadPatch_CodeCaveStart
.area DownloadPatch_PayloadStart-DownloadPatch_CodeCaveStart
DownloadPatch_Trampoline:
    push {r0-r3,r12,lr}
    sub sp,sp,#8
    mrs r12,cpsr
    str r12,[sp]
    mov r0,r7
    bl DownloadPatch_SaveBankData
    ldr r12,[sp]
    msr cpsr_f,r12
    add sp,sp,#8
    pop {r0-r3,r12,lr}
    ldr r8,=0x000BB528
    bx lr
    .pool
.endarea

.org DownloadPatch_PayloadStart
.area DownloadPatch_CodeCaveEnd-DownloadPatch_PayloadStart
DownloadPatch_PayloadBegin:
    .importobj "../../build/1-download_patch/download_patch.o"
DownloadPatch_PayloadEnd:
.endarea

.close
