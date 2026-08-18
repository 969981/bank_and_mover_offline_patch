.3ds
.arm
.relativeinclude on

.include "../../include/symbol.inc"

.definelabel DownloadPatch_HookAddress, MoverDownload_ConsumeBankData + 0x18
.definelabel DownloadPatch_CodeCaveStart, 0x0028D5F0
.definelabel DownloadPatch_PayloadStart, 0x0028D670
.definelabel DownloadPatch_CodeCaveEnd, 0x0028E000

.open "../../00040000000C9C00.code", "../../build/1-download_patch/00040000000C9C00.code", 0x00100000

// r8 already contains the successful download's complete bankdata pointer.
// Replace the original mov r5,#0 and reproduce it in the trampoline.
// r8 已保存下载成功后的完整 bankdata 指针。
// 覆盖原来的 mov r5,#0，并在跳板中重放该指令。
.org DownloadPatch_HookAddress
    bl DownloadPatch_Trampoline

.org DownloadPatch_CodeCaveStart
.area DownloadPatch_PayloadStart-DownloadPatch_CodeCaveStart
DownloadPatch_Trampoline:
    push {r0-r3,r12,lr}
    sub sp,sp,#8
    mrs r12,cpsr
    str r12,[sp]
    mov r0,r8
    bl DownloadPatch_SaveBankData
    ldr r12,[sp]
    msr cpsr_f,r12
    add sp,sp,#8
    pop {r0-r3,r12,lr}
    mov r5,#0
    bx lr
.endarea

.org DownloadPatch_PayloadStart
.area DownloadPatch_CodeCaveEnd-DownloadPatch_PayloadStart
DownloadPatch_PayloadBegin:
    .importobj "../../build/1-download_patch/download_patch.o"
DownloadPatch_PayloadEnd:
.endarea

.close
