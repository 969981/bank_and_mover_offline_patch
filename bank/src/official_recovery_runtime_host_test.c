#include <assert.h>
#include "official_recovery_runtime.h"

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
    OfficialRecoveryAutoRuntime runtime;
    OfficialRecoveryRecord server=tx(),out={0};
    OfficialRecoveryAutoAction action;

    OfficialRecoveryAutoRuntime_Init(&runtime);
    assert(OfficialRecoveryMarkerIO_IsEmpty(runtime.marker));
    assert(OfficialRecoveryAutoRuntime_OnBulkApplied(&runtime,7u));
    assert(OfficialRecoveryMarker_IsPending(runtime.marker,7u));
    assert(OfficialRecoveryAutoRuntime_OnTransactionBound(
        &runtime,&server,7u));
    assert(OfficialRecoveryMarker_MatchesServer(runtime.marker,&server,7u));

    action=OfficialRecoveryAutoRuntime_OnMismatch(
        &runtime,1,&server,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_ROLLBACK);
    assert(out.status==1u);
    assert(out.dataId==server.dataId);
    assert(out.transactionPassword==server.transactionPassword);
    assert(out.curVersion==server.curVersion);
    assert(out.updateVersion==server.updateVersion);
    assert(out.size==server.size);

    action=OfficialRecoveryAutoRuntime_OnMismatch(
        &runtime,1,&server,7u,1,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_STOCK);

    server.curVersion++;
    action=OfficialRecoveryAutoRuntime_OnMismatch(
        &runtime,1,&server,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_BLOCK);
    server.curVersion--;

    action=OfficialRecoveryAutoRuntime_OnMismatch(
        &runtime,0,0,7u,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_LOCAL_CLEANUP);
    assert(OfficialRecoveryMarkerIO_IsEmpty(runtime.marker));

    assert(OfficialRecoveryAutoRuntime_OnBulkApplied(&runtime,7u));
    assert(OfficialRecoveryAutoRuntime_OnTransactionBound(
        &runtime,&server,7u));
    OfficialRecoveryAutoRuntime_OnRemoteResolved(&runtime);
    assert(OfficialRecoveryMarkerIO_IsEmpty(runtime.marker));
    return 0;
}
