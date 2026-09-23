#ifndef BANK_OFFICIAL_RECOVERY_SMART_H
#define BANK_OFFICIAL_RECOVERY_SMART_H

#include "official_recovery_probe.h"
#include "official_recovery_marker.h"

typedef enum {
    OFFICIAL_RECOVERY_SMART_STOCK=0,
    OFFICIAL_RECOVERY_SMART_ROLLBACK=1,
    OFFICIAL_RECOVERY_SMART_COMMIT=2,
    OFFICIAL_RECOVERY_SMART_LOCAL_CLEANUP=3,
    OFFICIAL_RECOVERY_SMART_BLOCK=4
} OfficialRecoverySmartAction;

OfficialRecoverySmartAction OfficialRecoverySmart_Decide(
    int serverPending,const OfficialRecoveryRecord *server,unsigned profile,
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    int stockLocalMatched,int stockGameMatched);

#endif
