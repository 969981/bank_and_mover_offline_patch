#include <assert.h>
#include "official_recovery_probe.h"

static OfficialRecoveryRecord rec(unsigned long long id,unsigned version,unsigned status)
{
    OfficialRecoveryRecord r={0};
    r.dataId=id;
    r.curVersion=version;
    r.status=(unsigned char)status;
    return r;
}

int main(void)
{
    OfficialRecoveryRecord local=rec(0x1111222233334444ULL,7,2);
    OfficialRecoveryRecord game=rec(0x1111222233334444ULL,7,1);
    OfficialRecoveryDecision d;

    d=OfficialRecovery_Classify(0x1111222233334444ULL,7,&local,&game);
    assert(d.action==OFFICIAL_RECOVERY_COMMIT);
    assert(d.source==OFFICIAL_RECOVERY_SOURCE_LOCAL);

    local.status=1;
    d=OfficialRecovery_Classify(local.dataId,7,&local,&game);
    assert(d.action==OFFICIAL_RECOVERY_ROLLBACK);
    assert(d.source==OFFICIAL_RECOVERY_SOURCE_LOCAL);

    local.dataId=0x9999;
    d=OfficialRecovery_Classify(game.dataId,7,&local,&game);
    assert(d.action==OFFICIAL_RECOVERY_ROLLBACK);
    assert(d.source==OFFICIAL_RECOVERY_SOURCE_GAME);

    game.status=2;
    d=OfficialRecovery_Classify(game.dataId,7,&local,&game);
    assert(d.action==OFFICIAL_RECOVERY_COMMIT);
    assert(d.source==OFFICIAL_RECOVERY_SOURCE_GAME);

    game.curVersion=8;
    d=OfficialRecovery_Classify(game.dataId,7,&local,&game);
    assert(d.action==OFFICIAL_RECOVERY_BLOCK);
    assert(d.source==OFFICIAL_RECOVERY_SOURCE_NONE);

    game.curVersion=7;
    game.status=0;
    d=OfficialRecovery_Classify(game.dataId,7,&local,&game);
    assert(d.action==OFFICIAL_RECOVERY_BLOCK);

    local.dataId=game.dataId;
    local.curVersion=7;
    local.status=0;
    game.status=2;
    d=OfficialRecovery_Classify(game.dataId,7,&local,&game);
    assert(d.action==OFFICIAL_RECOVERY_COMMIT);
    assert(d.source==OFFICIAL_RECOVERY_SOURCE_GAME);

    {
        OfficialRecoveryRecord server={0}, rebuilt={0};
        server.dataId=0xABCDEF0123456789ULL;
        server.transactionPassword=0x1020304050607080ULL;
        server.curVersion=41;
        server.updateVersion=42;
        server.size=0xBB518u;
        server.status=2; /* not copied: explicit repair requests rollback */

        assert(OfficialRecovery_BuildRollbackRecord(&server,&rebuilt)==1);
        assert(rebuilt.dataId==server.dataId);
        assert(rebuilt.transactionPassword==server.transactionPassword);
        assert(rebuilt.curVersion==server.curVersion);
        assert(rebuilt.updateVersion==server.updateVersion);
        assert(rebuilt.size==server.size);
        assert(rebuilt.status==1u);
        assert(OfficialRecovery_RecordMatchesServer(&rebuilt,server.dataId,server.curVersion));

        assert(OfficialRecovery_BuildRollbackRecord(0,&rebuilt)==0);
        assert(OfficialRecovery_BuildRollbackRecord(&server,0)==0);
    }

    return 0;
}