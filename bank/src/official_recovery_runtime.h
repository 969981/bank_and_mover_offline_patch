#ifndef BANK_OFFICIAL_RECOVERY_RUNTIME_H
#define BANK_OFFICIAL_RECOVERY_RUNTIME_H

#include "official_recovery_auto_rollback.h"

/* Host-test model of the actual Variant-A state18 shim. */
OfficialRecoveryAutoAction OfficialRecoveryAutoRuntime_OnMismatch(
    int serverPending,const OfficialRecoveryRecord *server,
    int stockLocalMatched,int stockGameMatched,
    OfficialRecoveryRecord *recoveryOut);

#endif
