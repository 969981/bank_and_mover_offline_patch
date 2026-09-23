#include "official_recovery_runtime.h"

OfficialRecoveryAutoAction OfficialRecoveryAutoRuntime_OnMismatch(
    int serverPending,const OfficialRecoveryRecord *server,
    int stockLocalMatched,int stockGameMatched,
    OfficialRecoveryRecord *recoveryOut)
{
    OfficialRecoveryAutoAction action=OfficialRecoveryAutoRollback_Decide(
        serverPending,server,stockLocalMatched,stockGameMatched);
    if (action==OFFICIAL_RECOVERY_AUTO_ROLLBACK) {
        if (!OfficialRecovery_BuildRollbackRecord(server,recoveryOut))
            return OFFICIAL_RECOVERY_AUTO_BLOCK;
    }
    return action;
}
