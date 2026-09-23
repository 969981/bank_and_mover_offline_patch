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

#endif
