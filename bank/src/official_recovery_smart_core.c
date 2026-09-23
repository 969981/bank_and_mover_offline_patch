#include "official_recovery_smart.h"

static int markerIsBoundForProfile(
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],unsigned profile)
{
    OfficialRecoveryRecord saved;
    OfficialRecoveryStage stage;
    unsigned savedProfile=0,flags=0;
    if (!marker || profile<1u || profile>8u) return 0;
    if (!OfficialRecoveryMarker_Decode(marker,&saved,&savedProfile,&flags) ||
        !OfficialRecoveryMarker_GetStage(marker,&stage)) return 0;
    (void)saved;
    return savedProfile==profile &&
        (flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED)!=0u &&
        (flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_PENDING)==0u &&
        stage>=OFFICIAL_RECOVERY_STAGE_TX_BOUND;
}

OfficialRecoverySmartAction OfficialRecoverySmart_Decide(
    int serverPending,const OfficialRecoveryRecord *server,unsigned profile,
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    int stockLocalMatched,int stockGameMatched)
{
    OfficialRecoveryStage stage;
    if (stockLocalMatched || stockGameMatched) return OFFICIAL_RECOVERY_SMART_STOCK;
    if (!serverPending) {
        return markerIsBoundForProfile(marker,profile) ?
            OFFICIAL_RECOVERY_SMART_LOCAL_CLEANUP : OFFICIAL_RECOVERY_SMART_STOCK;
    }
    if (!server || !marker ||
        !OfficialRecoveryMarker_MatchesServer(marker,server,profile))
        return OFFICIAL_RECOVERY_SMART_BLOCK;
    if (!OfficialRecoveryMarker_GetStage(marker,&stage))
        return OFFICIAL_RECOVERY_SMART_BLOCK;
    switch (stage) {
    case OFFICIAL_RECOVERY_STAGE_TX_BOUND:
    case OFFICIAL_RECOVERY_STAGE_GAME_SAVE_STARTED:
        return OFFICIAL_RECOVERY_SMART_ROLLBACK;
    case OFFICIAL_RECOVERY_STAGE_GAME_SAVE_OK:
    case OFFICIAL_RECOVERY_STAGE_REMOTE_COMPLETE_STARTED:
        return OFFICIAL_RECOVERY_SMART_COMMIT;
    default:
        return OFFICIAL_RECOVERY_SMART_BLOCK;
    }
}
