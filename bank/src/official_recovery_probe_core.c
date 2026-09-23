#include "official_recovery_probe.h"

int OfficialRecovery_RecordMatchesServer(const OfficialRecoveryRecord *record,
    unsigned long long serverDataId,unsigned serverCurVersion)
{
    return record && record->dataId==serverDataId && record->curVersion==serverCurVersion;
}

static OfficialRecoveryDecision decide(const OfficialRecoveryRecord *record,
    OfficialRecoverySource source)
{
    OfficialRecoveryDecision d={OFFICIAL_RECOVERY_BLOCK,OFFICIAL_RECOVERY_SOURCE_NONE};
    if (!record) return d;
    if (record->status==1u) {
        d.action=OFFICIAL_RECOVERY_ROLLBACK;
        d.source=source;
    }
    else if (record->status==2u) {
        d.action=OFFICIAL_RECOVERY_COMMIT;
        d.source=source;
    }
    return d;
}

OfficialRecoveryDecision OfficialRecovery_Classify(unsigned long long serverDataId,
    unsigned serverCurVersion,const OfficialRecoveryRecord *localRecord,
    const OfficialRecoveryRecord *gameRecord)
{
    OfficialRecoveryDecision d={OFFICIAL_RECOVERY_BLOCK,OFFICIAL_RECOVERY_SOURCE_NONE};
    if (OfficialRecovery_RecordMatchesServer(localRecord,serverDataId,serverCurVersion)) {
        d=decide(localRecord,OFFICIAL_RECOVERY_SOURCE_LOCAL);
        if (d.action!=OFFICIAL_RECOVERY_BLOCK) return d;
    }
    if (OfficialRecovery_RecordMatchesServer(gameRecord,serverDataId,serverCurVersion))
        return decide(gameRecord,OFFICIAL_RECOVERY_SOURCE_GAME);
    return d;
}

int OfficialRecovery_BuildRollbackRecord(const OfficialRecoveryRecord *server,
    OfficialRecoveryRecord *gameOut)
{
    if (!server || !gameOut) return 0;
    gameOut->dataId=server->dataId;
    gameOut->transactionPassword=server->transactionPassword;
    gameOut->curVersion=server->curVersion;
    gameOut->updateVersion=server->updateVersion;
    gameOut->size=server->size;
    gameOut->status=1u;
    return 1;
}
