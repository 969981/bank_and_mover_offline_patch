#ifndef BANK_OFFICIAL_RECOVERY_AUTO_ROLLBACK_H
#define BANK_OFFICIAL_RECOVERY_AUTO_ROLLBACK_H

#include "official_recovery_probe.h"
#include "official_recovery_marker.h"

typedef enum {
    OFFICIAL_RECOVERY_AUTO_STOCK=0,
    OFFICIAL_RECOVERY_AUTO_ROLLBACK=1,
    OFFICIAL_RECOVERY_AUTO_LOCAL_CLEANUP=2,
    OFFICIAL_RECOVERY_AUTO_BLOCK=3
} OfficialRecoveryAutoAction;

OfficialRecoveryAutoAction OfficialRecoveryAutoRollback_Decide(
    int serverPending,const OfficialRecoveryRecord *server,unsigned profile,
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    int stockLocalMatched,int stockGameMatched);

#endif
