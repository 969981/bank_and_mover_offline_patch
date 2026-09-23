#include "official_recovery_smart_runtime.h"

static int buildRecord(const OfficialRecoveryRecord *server,unsigned char status,
    OfficialRecoveryRecord *out)
{
    if (!server || !out) return 0;
    *out=*server;
    out->status=status;
    return 1;
}

void OfficialRecoverySmartRuntime_Init(OfficialRecoverySmartRuntime *runtime)
{
    if (runtime) OfficialRecoveryMarkerIO_Invalidate(runtime->marker);
}

int OfficialRecoverySmartRuntime_OnBulkApplied(
    OfficialRecoverySmartRuntime *runtime,unsigned profile)
{
    return runtime && OfficialRecoveryMarker_EncodePending(runtime->marker,profile);
}

int OfficialRecoverySmartRuntime_OnTransactionBound(
    OfficialRecoverySmartRuntime *runtime,
    const OfficialRecoveryRecord *server,unsigned profile)
{
    return runtime && OfficialRecoveryMarker_BindTransaction(
        runtime->marker,server,profile);
}

int OfficialRecoverySmartRuntime_OnGameSaveStarted(
    OfficialRecoverySmartRuntime *runtime)
{
    return runtime && OfficialRecoveryMarker_AdvanceStage(runtime->marker,
        OFFICIAL_RECOVERY_STAGE_GAME_SAVE_STARTED);
}

int OfficialRecoverySmartRuntime_OnGameSaveSucceeded(
    OfficialRecoverySmartRuntime *runtime)
{
    return runtime && OfficialRecoveryMarker_AdvanceStage(runtime->marker,
        OFFICIAL_RECOVERY_STAGE_GAME_SAVE_OK);
}

int OfficialRecoverySmartRuntime_OnRemoteCompleteStarted(
    OfficialRecoverySmartRuntime *runtime)
{
    return runtime && OfficialRecoveryMarker_AdvanceStage(runtime->marker,
        OFFICIAL_RECOVERY_STAGE_REMOTE_COMPLETE_STARTED);
}

OfficialRecoverySmartAction OfficialRecoverySmartRuntime_OnMismatch(
    OfficialRecoverySmartRuntime *runtime,int serverPending,
    const OfficialRecoveryRecord *server,unsigned profile,
    int stockLocalMatched,int stockGameMatched,
    OfficialRecoveryRecord *recoveryOut)
{
    OfficialRecoverySmartAction action;
    if (!runtime) return OFFICIAL_RECOVERY_SMART_BLOCK;
    action=OfficialRecoverySmart_Decide(serverPending,server,profile,
        runtime->marker,stockLocalMatched,stockGameMatched);
    if (action==OFFICIAL_RECOVERY_SMART_ROLLBACK) {
        if (!buildRecord(server,1u,recoveryOut))
            return OFFICIAL_RECOVERY_SMART_BLOCK;
    } else if (action==OFFICIAL_RECOVERY_SMART_COMMIT) {
        if (!buildRecord(server,2u,recoveryOut))
            return OFFICIAL_RECOVERY_SMART_BLOCK;
    } else if (action==OFFICIAL_RECOVERY_SMART_LOCAL_CLEANUP) {
        OfficialRecoveryMarkerIO_Invalidate(runtime->marker);
    }
    return action;
}

void OfficialRecoverySmartRuntime_OnRemoteResolved(
    OfficialRecoverySmartRuntime *runtime)
{
    if (runtime) OfficialRecoveryMarkerIO_Invalidate(runtime->marker);
}
