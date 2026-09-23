#ifndef BANK_OFFICIAL_RECOVERY_AUTO_ROLLBACK_H
#define BANK_OFFICIAL_RECOVERY_AUTO_ROLLBACK_H

#include "official_recovery_probe.h"

typedef enum {
    OFFICIAL_RECOVERY_AUTO_STOCK=0,
    OFFICIAL_RECOVERY_AUTO_ROLLBACK=1,
    OFFICIAL_RECOVERY_AUTO_BLOCK=2
} OfficialRecoveryAutoAction;

/*
 * Variant A intentionally has no tool-ownership marker. Stock matching records
 * always win. If stock cannot match either recovery record but a current server
 * pending transaction exists, choose Rollback as the conservative escape from
 * the otherwise permanent mismatch state.
 */
OfficialRecoveryAutoAction OfficialRecoveryAutoRollback_Decide(
    int serverPending,const OfficialRecoveryRecord *server,
    int stockLocalMatched,int stockGameMatched);

#endif
