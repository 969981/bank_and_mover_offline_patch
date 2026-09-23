#ifndef BANK_OFFICIAL_RECOVERY_RUNTIME_H
#define BANK_OFFICIAL_RECOVERY_RUNTIME_H

#include "official_recovery_auto_rollback.h"
#include "official_recovery_marker_io.h"

typedef struct {
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE];
} OfficialRecoveryAutoRuntime;

void OfficialRecoveryAutoRuntime_Init(OfficialRecoveryAutoRuntime *runtime);
int OfficialRecoveryAutoRuntime_OnBulkApplied(
    OfficialRecoveryAutoRuntime *runtime,unsigned profile);
int OfficialRecoveryAutoRuntime_OnTransactionBound(
    OfficialRecoveryAutoRuntime *runtime,
    const OfficialRecoveryRecord *server,unsigned profile);
OfficialRecoveryAutoAction OfficialRecoveryAutoRuntime_OnMismatch(
    OfficialRecoveryAutoRuntime *runtime,int serverPending,
    const OfficialRecoveryRecord *server,unsigned profile,
    int stockLocalMatched,int stockGameMatched,
    OfficialRecoveryRecord *recoveryOut);
void OfficialRecoveryAutoRuntime_OnRemoteResolved(
    OfficialRecoveryAutoRuntime *runtime);

#endif
