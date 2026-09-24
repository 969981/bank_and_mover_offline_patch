#include "official_existing_lock_recovery.h"

OfficialExistingLockDecision OfficialExistingLock_PrepareGameRollback(
    int stockMismatch,
    const OfficialExistingLockServerTx *server,
    OfficialExistingLockGameRecord *gameOut)
{
    if (!stockMismatch || !server || !gameOut)
        return OFFICIAL_EXISTING_LOCK_KEEP_STOCK_MISMATCH;

    gameOut->dataId=server->dataId;
    gameOut->transactionPassword=server->transactionPassword;
    gameOut->curVersion=server->curVersion;
    gameOut->updateVersion=server->updateVersion;
    gameOut->size=server->size;
    gameOut->status=1u;
    return OFFICIAL_EXISTING_LOCK_ROUTE_STATE17_ROLLBACK;
}
