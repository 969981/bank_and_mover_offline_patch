#include <assert.h>
#include "official_existing_lock_recovery.h"

static OfficialExistingLockServerTx tx(void)
{
    OfficialExistingLockServerTx t={0};
    t.dataId=0x1122334455667788ULL;
    t.curVersion=17u;
    t.updateVersion=18u;
    t.size=0xBB518u;
    t.transactionPassword=0x8877665544332211ULL;
    return t;
}

int main(void)
{
    OfficialExistingLockServerTx server=tx();
    OfficialExistingLockGameRecord out={0};
    OfficialExistingLockDecision d;

    d=OfficialExistingLock_PrepareGameRollback(1,&server,&out);
    assert(d==OFFICIAL_EXISTING_LOCK_ROUTE_STATE17_ROLLBACK);
    assert(out.dataId==server.dataId);
    assert(out.transactionPassword==server.transactionPassword);
    assert(out.curVersion==server.curVersion);
    assert(out.updateVersion==server.updateVersion);
    assert(out.size==server.size);
    assert(out.status==1u);

    out.dataId=0xA5A5A5A5A5A5A5A5ULL;
    d=OfficialExistingLock_PrepareGameRollback(0,&server,&out);
    assert(d==OFFICIAL_EXISTING_LOCK_KEEP_STOCK_MISMATCH);
    assert(out.dataId==0xA5A5A5A5A5A5A5A5ULL);

    d=OfficialExistingLock_PrepareGameRollback(1,0,&out);
    assert(d==OFFICIAL_EXISTING_LOCK_KEEP_STOCK_MISMATCH);

    d=OfficialExistingLock_PrepareGameRollback(1,&server,0);
    assert(d==OFFICIAL_EXISTING_LOCK_KEEP_STOCK_MISMATCH);

    {
        OfficialExistingLockGameRecord second={0};
        d=OfficialExistingLock_PrepareGameRollback(1,&server,&second);
        assert(d==OFFICIAL_EXISTING_LOCK_ROUTE_STATE17_ROLLBACK);
        assert(second.dataId==server.dataId);
        assert(second.transactionPassword==server.transactionPassword);
        assert(second.curVersion==server.curVersion);
        assert(second.updateVersion==server.updateVersion);
        assert(second.size==server.size);
        assert(second.status==1u);
    }

    return 0;
}
