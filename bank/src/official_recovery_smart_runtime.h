#ifndef BANK_OFFICIAL_RECOVERY_SMART_RUNTIME_H
#define BANK_OFFICIAL_RECOVERY_SMART_RUNTIME_H

#include "official_recovery_smart.h"
#include "official_recovery_marker_io.h"

typedef struct {
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE];
} OfficialRecoverySmartRuntime;

void OfficialRecoverySmartRuntime_Init(OfficialRecoverySmartRuntime *runtime);
int OfficialRecoverySmartRuntime_OnBulkApplied(
    OfficialRecoverySmartRuntime *runtime,unsigned profile);
int OfficialRecoverySmartRuntime_OnTransactionBound(
    OfficialRecoverySmartRuntime *runtime,
    const OfficialRecoveryRecord *server,unsigned profile);
int OfficialRecoverySmartRuntime_OnGameSaveStarted(
    OfficialRecoverySmartRuntime *runtime);
int OfficialRecoverySmartRuntime_OnGameSaveSucceeded(
    OfficialRecoverySmartRuntime *runtime);
int OfficialRecoverySmartRuntime_OnRemoteCompleteStarted(
    OfficialRecoverySmartRuntime *runtime);
OfficialRecoverySmartAction OfficialRecoverySmartRuntime_OnMismatch(
    OfficialRecoverySmartRuntime *runtime,int serverPending,
    const OfficialRecoveryRecord *server,unsigned profile,
    int stockLocalMatched,int stockGameMatched,
    OfficialRecoveryRecord *recoveryOut);
void OfficialRecoverySmartRuntime_OnRemoteResolved(
    OfficialRecoverySmartRuntime *runtime);

#endif
