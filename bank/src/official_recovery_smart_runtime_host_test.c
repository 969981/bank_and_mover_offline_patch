#include <assert.h>
#include "official_recovery_smart_runtime.h"

static OfficialRecoveryRecord tx(void)
{
    OfficialRecoveryRecord r={0};
    r.dataId=11u;
    r.transactionPassword=22u;
    r.curVersion=3u;
    r.updateVersion=4u;
    r.size=0xBB518u;
    return r;
}

int main(void)
{
    OfficialRecoverySmartRuntime runtime;
    OfficialRecoveryRecord server=tx(),out={0};
    OfficialRecoverySmartAction action;
    OfficialRecoveryStage stage;

    OfficialRecoverySmartRuntime_Init(&runtime);
    assert(OfficialRecoveryMarkerIO_IsEmpty(runtime.marker));
    assert(OfficialRecoverySmartRuntime_OnBulkApplied(&runtime,7u));
    assert(OfficialRecoverySmartRuntime_OnTransactionBound(
        &runtime,&server,7u));

    action=OfficialRecoverySmartRuntime_OnMismatch(
        &runtime,1,&server,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_SMART_ROLLBACK);
    assert(out.status==1u);

    assert(OfficialRecoverySmartRuntime_OnGameSaveStarted(&runtime));
    action=OfficialRecoverySmartRuntime_OnMismatch(
        &runtime,1,&server,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_SMART_ROLLBACK);
    assert(out.status==1u);

    assert(OfficialRecoverySmartRuntime_OnGameSaveSucceeded(&runtime));
    action=OfficialRecoverySmartRuntime_OnMismatch(
        &runtime,1,&server,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_SMART_COMMIT);
    assert(out.status==2u);

    assert(OfficialRecoverySmartRuntime_OnRemoteCompleteStarted(&runtime));
    assert(OfficialRecoveryMarker_GetStage(runtime.marker,&stage));
    assert(stage==OFFICIAL_RECOVERY_STAGE_REMOTE_COMPLETE_STARTED);
    action=OfficialRecoverySmartRuntime_OnMismatch(
        &runtime,1,&server,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_SMART_COMMIT);
    assert(out.status==2u);

    OfficialRecoverySmartRuntime_OnRemoteResolved(&runtime);
    assert(OfficialRecoveryMarkerIO_IsEmpty(runtime.marker));

    assert(OfficialRecoverySmartRuntime_OnBulkApplied(&runtime,7u));
    assert(OfficialRecoverySmartRuntime_OnTransactionBound(
        &runtime,&server,7u));
    server.curVersion++;
    action=OfficialRecoverySmartRuntime_OnMismatch(
        &runtime,1,&server,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_SMART_BLOCK);
    return 0;
}
