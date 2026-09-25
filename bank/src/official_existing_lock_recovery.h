#ifndef BANK_OFFICIAL_EXISTING_LOCK_RECOVERY_H
#define BANK_OFFICIAL_EXISTING_LOCK_RECOVERY_H

typedef struct {
    unsigned long long dataId;
    unsigned curVersion;
    unsigned updateVersion;
    unsigned size;
    unsigned reserved;
    unsigned long long transactionPassword;
} OfficialExistingLockServerTx;

typedef struct {
    unsigned long long dataId;
    unsigned long long transactionPassword;
    unsigned curVersion;
    unsigned updateVersion;
    unsigned size;
    unsigned char status;
} OfficialExistingLockGameRecord;

typedef enum {
    OFFICIAL_EXISTING_LOCK_KEEP_STOCK_MISMATCH=0,
    OFFICIAL_EXISTING_LOCK_ROUTE_STATE17_ROLLBACK=1,
    OFFICIAL_EXISTING_LOCK_ROUTE_STATE17_PERSIST_REPAIR=2
} OfficialExistingLockDecision;

OfficialExistingLockDecision OfficialExistingLock_PrepareGameRollback(
    int stockMismatch,
    const OfficialExistingLockServerTx *server,
    OfficialExistingLockGameRecord *gameOut);

#endif
