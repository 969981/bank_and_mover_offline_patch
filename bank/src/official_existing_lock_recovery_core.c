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
     * 3 is a Recovery-C-only transient marker.  The production state17 hook
     * consumes it before any game save, restores stock rollback status=1, and
     * records a state17-local result marker so only this synthetic recovery
     * disconnects after successful cleanup.  Ordinary stock status 1/2 paths
     * are unchanged.
     */
    gameOut->status=3u;
    return OFFICIAL_EXISTING_LOCK_ROUTE_STATE17_ROLLBACK;
}
