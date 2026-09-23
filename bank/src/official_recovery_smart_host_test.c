#include <assert.h>
#include "official_recovery_smart.h"

static OfficialRecoveryRecord tx(void)
{
    OfficialRecoveryRecord r={0};
    r.dataId=1u;
    r.transactionPassword=2u;
    r.curVersion=3u;
    r.updateVersion=4u;
    r.size=0xBB518u;
    return r;
}

int main(void)
{
    OfficialRecoveryRecord server=tx();
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE];

    assert(OfficialRecoveryMarker_EncodePending(marker,7u));
    assert(OfficialRecoveryMarker_BindTransaction(marker,&server,7u));
    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_SMART_ROLLBACK);

    assert(OfficialRecoveryMarker_AdvanceStage(marker,
        OFFICIAL_RECOVERY_STAGE_GAME_SAVE_STARTED));
    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_SMART_ROLLBACK);

    assert(OfficialRecoveryMarker_AdvanceStage(marker,
        OFFICIAL_RECOVERY_STAGE_GAME_SAVE_OK));
    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_SMART_COMMIT);

    assert(OfficialRecoveryMarker_AdvanceStage(marker,
        OFFICIAL_RECOVERY_STAGE_REMOTE_COMPLETE_STARTED));
    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_SMART_COMMIT);

    assert(OfficialRecoveryMarker_AdvanceStage(marker,
        OFFICIAL_RECOVERY_STAGE_DONE));
    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_SMART_BLOCK);
    assert(OfficialRecoverySmart_Decide(0,0,7u,marker,0,0)==
        OFFICIAL_RECOVERY_SMART_LOCAL_CLEANUP);

    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,1,0)==
        OFFICIAL_RECOVERY_SMART_STOCK);
    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,0,1)==
        OFFICIAL_RECOVERY_SMART_STOCK);

    server.curVersion++;
    assert(OfficialRecoverySmart_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_SMART_BLOCK);
    return 0;
}
