#include "official_recovery_runtime.h"

void OfficialRecoveryAutoRuntime_Init(OfficialRecoveryAutoRuntime *runtime)
{
    if (!runtime) return;
    OfficialRecoveryMarkerIO_Invalidate(runtime->marker);
}

int OfficialRecoveryAutoRuntime_OnBulkApplied(
    OfficialRecoveryAutoRuntime *runtime,unsigned profile)
{
    return runtime && OfficialRecoveryMarker_EncodePending(runtime->marker,profile);
}

int OfficialRecoveryAutoRuntime_OnTransactionBound(
    OfficialRecoveryAutoRuntime *runtime,
    const OfficialRecoveryRecord *server,unsigned profile)
{
    return runtime && OfficialRecoveryMarker_BindTransaction(
        runtime->marker,server,profile);
}

OfficialRecoveryAutoAction OfficialRecoveryAutoRuntime_OnMismatch(
    OfficialRecoveryAutoRuntime *runtime,int serverPending,
    const OfficialRecoveryRecord *server,unsigned profile,
    int stockLocalMatched,int stockGameMatched,
    OfficialRecoveryRecord *recoveryOut)
{
    OfficialRecoveryAutoAction action;
    if (!runtime) return OFFICIAL_RECOVERY_AUTO_BLOCK;
    action=OfficialRecoveryAutoRollback_Decide(serverPending,server,profile,
        runtime->marker,stockLocalMatched,stockGameMatched);
    if (action==OFFICIAL_RECOVERY_AUTO_ROLLBACK) {
        if (!OfficialRecovery_BuildRollbackRecord(server,recoveryOut))
            return OFFICIAL_RECOVERY_AUTO_BLOCK;
    } else if (action==OFFICIAL_RECOVERY_AUTO_LOCAL_CLEANUP) {
        OfficialRecoveryMarkerIO_Invalidate(runtime->marker);
    }
    return action;
}

void OfficialRecoveryAutoRuntime_OnRemoteResolved(
    OfficialRecoveryAutoRuntime *runtime)
{
    if (!runtime) return;
    OfficialRecoveryMarkerIO_Invalidate(runtime->marker);
}
