#ifndef BANK_OFFICIAL_RECOVERY_PROBE_H
#define BANK_OFFICIAL_RECOVERY_PROBE_H

typedef struct {
    unsigned long long dataId;
    unsigned long long transactionPassword;
    unsigned curVersion;
    unsigned updateVersion;
    unsigned size;
    unsigned char status;
} OfficialRecoveryRecord;

typedef enum {
    OFFICIAL_RECOVERY_BLOCK=0,
    OFFICIAL_RECOVERY_COMMIT=1,
    OFFICIAL_RECOVERY_ROLLBACK=2
} OfficialRecoveryAction;

typedef enum {
    OFFICIAL_RECOVERY_SOURCE_NONE=0,
    OFFICIAL_RECOVERY_SOURCE_LOCAL=1,
    OFFICIAL_RECOVERY_SOURCE_GAME=2
} OfficialRecoverySource;

typedef struct {
    OfficialRecoveryAction action;
    OfficialRecoverySource source;
} OfficialRecoveryDecision;

int OfficialRecovery_RecordMatchesServer(const OfficialRecoveryRecord *record,
    unsigned long long serverDataId,unsigned serverCurVersion);
OfficialRecoveryDecision OfficialRecovery_Classify(unsigned long long serverDataId,
    unsigned serverCurVersion,const OfficialRecoveryRecord *localRecord,
    const OfficialRecoveryRecord *gameRecord);

/*
 * Build the exact transaction context state17 needs, but deliberately mark it
 * as rollback (status=1).  This helper is pure: it does not write game save or
 * call a remote method.  Runtime code must gate it to an explicitly approved
 * recovery context before persisting the resulting record.
 */
int OfficialRecovery_BuildRollbackRecord(const OfficialRecoveryRecord *server,
    OfficialRecoveryRecord *gameOut);

#endif
