#include "official_recovery_auto_rollback.h"

static int markerIsBoundForProfile(
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],unsigned profile)
{
    OfficialRecoveryRecord saved;
    unsigned savedProfile=0,flags=0;
    if (!marker || profile<1u || profile>8u) return 0;
    if (!OfficialRecoveryMarker_Decode(marker,&saved,&savedProfile,&flags)) return 0;
    (void)saved;
    return savedProfile==profile &&
        (flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED)!=0u &&
        (flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_PENDING)==0u;
}

OfficialRecoveryAutoAction OfficialRecoveryAutoRollback_Decide(
    int serverPending,const OfficialRecoveryRecord *server,unsigned profile,
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    int stockLocalMatched,int stockGameMatched)
{
    if (stockLocalMatched || stockGameMatched) return OFFICIAL_RECOVERY_AUTO_STOCK;
    if (!serverPending) {
        return markerIsBoundForProfile(marker,profile) ?
            OFFICIAL_RECOVERY_AUTO_LOCAL_CLEANUP : OFFICIAL_RECOVERY_AUTO_STOCK;
    }
    if (!server || !marker) return OFFICIAL_RECOVERY_AUTO_BLOCK;
    return OfficialRecoveryMarker_MatchesServer(marker,server,profile) ?
        OFFICIAL_RECOVERY_AUTO_ROLLBACK : OFFICIAL_RECOVERY_AUTO_BLOCK;
}
