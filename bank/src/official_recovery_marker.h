#ifndef BANK_OFFICIAL_RECOVERY_MARKER_H
#define BANK_OFFICIAL_RECOVERY_MARKER_H

#include "official_recovery_probe.h"

#define OFFICIAL_RECOVERY_MARKER_SIZE 48u
#define OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED 0x0001u
#define OFFICIAL_RECOVERY_MARKER_FLAG_BULK_PENDING 0x0002u

typedef enum {
    OFFICIAL_RECOVERY_STAGE_NONE=0,
    OFFICIAL_RECOVERY_STAGE_BULK_APPLIED=1,
    OFFICIAL_RECOVERY_STAGE_TX_BOUND=2,
    OFFICIAL_RECOVERY_STAGE_GAME_SAVE_STARTED=3,
    OFFICIAL_RECOVERY_STAGE_GAME_SAVE_OK=4,
    OFFICIAL_RECOVERY_STAGE_REMOTE_COMPLETE_STARTED=5,
    OFFICIAL_RECOVERY_STAGE_DONE=6
} OfficialRecoveryStage;

int OfficialRecoveryMarker_Encode(unsigned char out[OFFICIAL_RECOVERY_MARKER_SIZE],
    const OfficialRecoveryRecord *server,unsigned profile,unsigned flags);
int OfficialRecoveryMarker_EncodePending(
    unsigned char out[OFFICIAL_RECOVERY_MARKER_SIZE],unsigned profile);
int OfficialRecoveryMarker_BindTransaction(
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    const OfficialRecoveryRecord *server,unsigned profile);
int OfficialRecoveryMarker_IsPending(
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],unsigned profile);
int OfficialRecoveryMarker_Decode(const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    OfficialRecoveryRecord *serverOut,unsigned *profileOut,unsigned *flagsOut);
int OfficialRecoveryMarker_MatchesServer(
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    const OfficialRecoveryRecord *server,unsigned profile);
int OfficialRecoveryMarker_GetStage(
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    OfficialRecoveryStage *stageOut);
int OfficialRecoveryMarker_AdvanceStage(
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    OfficialRecoveryStage stage);
void OfficialRecoveryMarker_Rechecksum(
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE]);

#endif
