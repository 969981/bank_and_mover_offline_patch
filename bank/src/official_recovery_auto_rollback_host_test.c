#include <assert.h>
#include "official_recovery_auto_rollback.h"

static OfficialRecoveryRecord tx(void)
{
    OfficialRecoveryRecord r={0};
    r.dataId=0x1122334455667788ULL;
    r.transactionPassword=0x8877665544332211ULL;
    r.curVersion=41u;
    r.updateVersion=42u;
    r.size=0xBB518u;
    return r;
}

int main(void)
{
    OfficialRecoveryRecord server=tx();
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE]={0};

    assert(OfficialRecoveryMarker_EncodePending(marker,7u));
    assert(OfficialRecoveryMarker_BindTransaction(marker,&server,7u));
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_AUTO_ROLLBACK);

    assert(OfficialRecoveryAutoRollback_Decide(1,&server,7u,marker,1,0)==
        OFFICIAL_RECOVERY_AUTO_STOCK);
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,7u,marker,0,1)==
        OFFICIAL_RECOVERY_AUTO_STOCK);

    assert(OfficialRecoveryAutoRollback_Decide(0,0,7u,marker,0,0)==
        OFFICIAL_RECOVERY_AUTO_LOCAL_CLEANUP);

    assert(OfficialRecoveryMarker_EncodePending(marker,7u));
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_AUTO_BLOCK);

    assert(OfficialRecoveryMarker_BindTransaction(marker,&server,7u));
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,6u,marker,0,0)==
        OFFICIAL_RECOVERY_AUTO_BLOCK);

    server.curVersion++;
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_AUTO_BLOCK);
    server.curVersion--;

    marker[20]^=1u;
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,7u,marker,0,0)==
        OFFICIAL_RECOVERY_AUTO_BLOCK);
    return 0;
}
