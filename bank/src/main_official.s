.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official Bulk Sync + recovery-B transaction hardening.
// Every added executable byte remains inside the verified RX text tail. The
// recovery state hooks themselves only replace verified stock instructions.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

// Save-state hook sites verified against the exact Bank v1.5 image.
.definelabel RecoveryB_SaveCase1,               0x002B1DE4
.definelabel RecoveryB_SaveCase7Status,         0x002B1FFC
.definelabel RecoveryB_SaveCase8Result,         0x002B2090

// state18 recovery hook sites.
.definelabel RecoveryB_LocalStatusDecision,     0x002A8968
.definelabel RecoveryB_GameDataIdMismatch,      0x002A89D0
.definelabel RecoveryB_GameVersionMismatch,     0x002A89E0
.definelabel RecoveryB_GameMismatchDecision,    0x002A8A64
.definelabel RecoveryB_State18SetSubstate,       0x002A8980

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Existing Official Bulk Sync V3 hook.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// -----------------------------------------------------------------------------
// Recovery B: durable pre-RMC52 write-ahead journal
// -----------------------------------------------------------------------------
// case1 normally starts BankSave_SerializeAndStage immediately. The Thumb
// helper first diverts through stock case7/case8 to persist the exact current
// BankTransactionParam with private status=3. On the second pass it returns
// r0=r4, so the untouched BL at 0x002B1DE8 starts Stage normally.
.org RecoveryB_SaveCase1
    blx OfficialRecovery_WalCase1

// Stock case7 writes status=1. During only the private pre-Stage journal pass,
// select status=3 instead; ordinary rollback saves remain status=1.
.org RecoveryB_SaveCase7Status
    blx OfficialRecovery_WalSelectStatus

// Preserve stock case8 flags for ordinary saves. During the private journal
// pass, the helper routes success back to case1 and failure to state20 itself.
.org RecoveryB_SaveCase8Result
    blx OfficialRecovery_WalCase8Result

// -----------------------------------------------------------------------------
// Recovery B: smart state18 recovery
// -----------------------------------------------------------------------------
// At this point stock has already proven local dataId + curVersion equality and
// loaded the local recovery status into r0. The helper treats private status=3
// as a WAL only after also matching updateVersion, size and transactionPassword.
// It then routes through the stock state setter and therefore never returns to
// the overwritten CMP.
.org RecoveryB_LocalStatusDecision
    blx OfficialRecovery_WalLocalStatusB

// Hook only the two genuine current-game transaction mismatch edges. Do not
// hook the shared state=8 funnel because invalid game status reaches it too.
.org RecoveryB_GameDataIdMismatch
    bne RecoveryB_GameMismatchDecision
.org RecoveryB_GameVersionMismatch
    bne RecoveryB_GameMismatchDecision

// The stock block here was semantically redundant register clearing followed by
// `mov r0,#8 ; nop ; b 0x002A8980`. Reuse its 0x18 bytes without consuming the
// RX tail. state+0x88==2 exists only after an exact private WAL validation:
//   2 -> no durable game status=2 evidence, use stock Rollback state6
//   otherwise -> preserve stock Trainer/save mismatch state8.
// The ordinary invalid-game-status fallthrough also arrives here; stock sets
// +0x88=1 for a matched game record, so it still resolves to state8.
.org RecoveryB_GameMismatchDecision
.area 0x18
    ldrb r0,[r4,#0x88]
    cmp r0,#2
    moveq r0,#6
    movne r0,#8
    b RecoveryB_State18SetSubstate
    nop
.endarea

// -----------------------------------------------------------------------------
// RX-tail payload
// -----------------------------------------------------------------------------
.org OfficialBulk_CodeStart
.area OfficialBulk_CodeEnd-OfficialBulk_CodeStart
.arm

// 36-byte stock-to-Thumb dispatcher retained from Official Bulk Sync V3.
OfficialBulk_BankDataSyncDispatch:
    push {r4-r6,lr}
    mov r4,r0
    mrc p15,0,r1,c13,c0,3
    add r1,r1,#0x80
    ldr r12,=OfficialBulkSync_Process+1
    blx r12
    mov r0,r4
    b BankDataSyncState_Update + 4
    .pool

// Production packing is intentionally tight:
//   dispatcher 36 + recovery WAL 160 + bulk payload 1577 = 1773 / 1776 bytes.
.align 2
    .importobj "../build/official_recovery_wal_thumb.o"
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
