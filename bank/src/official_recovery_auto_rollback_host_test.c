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

    /* Stock has a valid recovery record: never interfere. */
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,1,0)==
        OFFICIAL_RECOVERY_AUTO_STOCK);
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,0,1)==
        OFFICIAL_RECOVERY_AUTO_STOCK);

    /* No pending server transaction: there is nothing to roll back. */
    assert(OfficialRecoveryAutoRollback_Decide(0,0,0,0)==
        OFFICIAL_RECOVERY_AUTO_STOCK);

    /* The defining Variant-A behavior: unresolved pending mismatch -> rollback. */
    assert(OfficialRecoveryAutoRollback_Decide(1,&server,0,0)==
        OFFICIAL_RECOVERY_AUTO_ROLLBACK);

    /* Fail closed if a caller claims pending without a usable server tx. */
    assert(OfficialRecoveryAutoRollback_Decide(1,0,0,0)==
        OFFICIAL_RECOVERY_AUTO_BLOCK);
    return 0;
}
