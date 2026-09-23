#ifndef BANK_OFFICIAL_RECOVERY_MARKER_H
#define BANK_OFFICIAL_RECOVERY_MARKER_H

#include "official_recovery_probe.h"

#define OFFICIAL_RECOVERY_MARKER_SIZE 48u
#define OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED 0x0001u
#define OFFICIAL_RECOVERY_MARKER_FLAG_BULK_PENDING 0x0002u

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
void OfficialRecoveryMarker_Rechecksum(
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE]);

#endif
