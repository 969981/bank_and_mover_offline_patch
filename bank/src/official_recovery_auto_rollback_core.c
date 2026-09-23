#include "official_recovery_auto_rollback.h"

OfficialRecoveryAutoAction OfficialRecoveryAutoRollback_Decide(
    int serverPending,const OfficialRecoveryRecord *server,
    int stockLocalMatched,int stockGameMatched)
{
    if (stockLocalMatched || stockGameMatched) return OFFICIAL_RECOVERY_AUTO_STOCK;
    if (!serverPending) return OFFICIAL_RECOVERY_AUTO_STOCK;
    return server ? OFFICIAL_RECOVERY_AUTO_ROLLBACK : OFFICIAL_RECOVERY_AUTO_BLOCK;
}
