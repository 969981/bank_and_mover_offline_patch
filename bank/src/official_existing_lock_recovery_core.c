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

    /*
     * 3 is a Recovery-C-only RAM marker.  C4 consumes it in stock state17,
     * immediately restores the record to stock Rollback status=1, then uses
     * the stock game-save writer to persist the exact CURRENT SERVER T1 before
     * any remote Commit/Rollback is attempted.  A successful persist ends the
     * current session; the next launch follows ordinary stock recovery.
     */
    gameOut->status=3u;
    return OFFICIAL_EXISTING_LOCK_ROUTE_STATE17_PERSIST_REPAIR;
}
