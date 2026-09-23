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
    OfficialRecoveryRecord server=tx(),out={0};
    OfficialRecoveryAutoAction action;

    action=OfficialRecoveryAutoRuntime_OnMismatch(1,&server,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_ROLLBACK);
    assert(out.status==1u);
    assert(out.dataId==server.dataId);
    assert(out.transactionPassword==server.transactionPassword);
    assert(out.curVersion==server.curVersion);
    assert(out.updateVersion==server.updateVersion);
    assert(out.size==server.size);

    action=OfficialRecoveryAutoRuntime_OnMismatch(1,&server,1,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_STOCK);
    action=OfficialRecoveryAutoRuntime_OnMismatch(1,&server,0,1,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_STOCK);
    action=OfficialRecoveryAutoRuntime_OnMismatch(0,0,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_STOCK);
    action=OfficialRecoveryAutoRuntime_OnMismatch(1,0,0,0,&out);
    assert(action==OFFICIAL_RECOVERY_AUTO_BLOCK);
    return 0;
}
