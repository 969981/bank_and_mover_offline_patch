.3ds
.arm
.relativeinclude on

.include "../include/symbol.inc"

// Official-only bulk sync. Keep every executable byte inside the real RX text
// tail padding. No .data/BSS region is repurposed as code or scratch storage.
.definelabel OfficialBulk_CodeStart, TextActualEnd
.definelabel OfficialBulk_CodeEnd,   TextMappedEnd

.open "../rom/exefs/00040000000C9B00.dec.code", "../build/00040000000C9B00.dec.code", 0x00100000

// Run before the stock state machine consumes its native callback status byte.
.org BankDataSyncState_Update
    b OfficialBulk_BankDataSyncDispatch

// Stock ordinary-Bank flow sets r0=12 here after a successful state-16 Bank
// download. State 12 is RewardEligibility and may enter state 13
// RewardReceive, which displays low-points, claimable-points, first-present,
// and related mileage/reward UI. Keep all mileage/reward data untouched and
// bypass only those UI states by selecting the stock Bank Box state (25).
//
// 原版普通 Bank 在 state 16 下载成功后会在这里将下一状态设为 12
//（里程/奖励资格判断），并可能继续进入 state 13（奖励领取），显示点数不足、
// 可领取、首次奖励等界面。这里只把下一状态改为原版 Bank Box state 25：
// 不领取、不清零、不修改服务器里程/奖励数据，也不改 state 12/13 本体。
.org BankFlow_SelectNextState + 0x248
    moveq r0,#25

.org OfficialBulk_CodeStart
.area OfficialBulk_CodeEnd-OfficialBulk_CodeStart
.arm

// The native BankDataSync state already tells us exactly when an ordinary
// game-linked Bank download finished: substate==2, callbackStatus==1 and
// specialFlag==0. The Thumb runtime checks those fields itself, so no global
// pending marker and no download-callback hook are needed.
//
// Important interworking rule: do not let the imported Thumb object call an
// ARM helper through R_ARM_THM_CALL. armips currently relocates that external
// Thumb->ARM call two bytes early on this payload. Fetch TLS here in ARM state
// and pass the command-buffer pointer as r1 instead.
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

.align 2
    .importobj "../build/official_bulk_sync_prod.o"
.endarea

.close
