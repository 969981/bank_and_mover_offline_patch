#include "official_recovery_marker.h"

#define MARKER_VERSION 1u
#define OFF_MAGIC 0u
#define OFF_VERSION 4u
#define OFF_FLAGS 6u
#define OFF_PROFILE 8u
#define OFF_DATA_ID 12u
#define OFF_PASSWORD 20u
#define OFF_CUR_VERSION 28u
#define OFF_UPDATE_VERSION 32u
#define OFF_SIZE 36u
#define OFF_CHECKSUM 44u

static void put16(unsigned char *p,unsigned v)
{
    p[0]=(unsigned char)v;
    p[1]=(unsigned char)(v>>8);
}

static unsigned get16(const unsigned char *p)
{
    return (unsigned)p[0]|((unsigned)p[1]<<8);
}

static void put32(unsigned char *p,unsigned v)
{
    p[0]=(unsigned char)v;
    p[1]=(unsigned char)(v>>8);
    p[2]=(unsigned char)(v>>16);
    p[3]=(unsigned char)(v>>24);
}

static unsigned get32(const unsigned char *p)
{
    return (unsigned)p[0]|((unsigned)p[1]<<8)|((unsigned)p[2]<<16)|((unsigned)p[3]<<24);
}

static void put64(unsigned char *p,unsigned long long v)
{
    unsigned i;
    for (i=0;i<8u;i++) {
        p[i]=(unsigned char)v;
        v>>=8;
    }
}

static unsigned long long get64(const unsigned char *p)
{
    unsigned i;
    unsigned long long v=0;
    for (i=0;i<8u;i++) v|=((unsigned long long)p[i])<<(i*8u);
    return v;
}

static unsigned checksum44(const unsigned char *p)
{
    unsigned i;
    unsigned h=2166136261u;
    for (i=0;i<44u;i++) {
        h^=(unsigned)p[i];
        h*=16777619u;
    }
    return h;
}

void OfficialRecoveryMarker_Rechecksum(
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE])
{
    if (!marker) return;
    put32(marker+OFF_CHECKSUM,checksum44(marker));
}

int OfficialRecoveryMarker_Encode(unsigned char out[OFFICIAL_RECOVERY_MARKER_SIZE],
    const OfficialRecoveryRecord *server,unsigned profile,unsigned flags)
{
    unsigned i;
    if (!out || !server || profile<1u || profile>8u) return 0;
    for (i=0;i<OFFICIAL_RECOVERY_MARKER_SIZE;i++) out[i]=0;
    out[OFF_MAGIC+0]='O';
    out[OFF_MAGIC+1]='B';
    out[OFF_MAGIC+2]='R';
    out[OFF_MAGIC+3]='X';
    put16(out+OFF_VERSION,MARKER_VERSION);
    put16(out+OFF_FLAGS,flags);
    out[OFF_PROFILE]=(unsigned char)profile;
    put64(out+OFF_DATA_ID,server->dataId);
    put64(out+OFF_PASSWORD,server->transactionPassword);
    put32(out+OFF_CUR_VERSION,server->curVersion);
    put32(out+OFF_UPDATE_VERSION,server->updateVersion);
    put32(out+OFF_SIZE,server->size);
    OfficialRecoveryMarker_Rechecksum(out);
    return 1;
}

int OfficialRecoveryMarker_Decode(const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    OfficialRecoveryRecord *serverOut,unsigned *profileOut,unsigned *flagsOut)
{
    unsigned profile,flags;
    if (!marker || !serverOut) return 0;
    if (marker[0]!='O' || marker[1]!='B' || marker[2]!='R' || marker[3]!='X') return 0;
    if (get16(marker+OFF_VERSION)!=MARKER_VERSION) return 0;
    if (get32(marker+OFF_CHECKSUM)!=checksum44(marker)) return 0;
    profile=marker[OFF_PROFILE];
    if (profile<1u || profile>8u) return 0;
    flags=get16(marker+OFF_FLAGS);
    serverOut->dataId=get64(marker+OFF_DATA_ID);
    serverOut->transactionPassword=get64(marker+OFF_PASSWORD);
    serverOut->curVersion=get32(marker+OFF_CUR_VERSION);
    serverOut->updateVersion=get32(marker+OFF_UPDATE_VERSION);
    serverOut->size=get32(marker+OFF_SIZE);
    serverOut->status=0u;
    if (profileOut) *profileOut=profile;
    if (flagsOut) *flagsOut=flags;
    return 1;
}

int OfficialRecoveryMarker_EncodePending(
    unsigned char out[OFFICIAL_RECOVERY_MARKER_SIZE],unsigned profile)
{
    OfficialRecoveryRecord empty={0};
    return OfficialRecoveryMarker_Encode(out,&empty,profile,
        OFFICIAL_RECOVERY_MARKER_FLAG_BULK_PENDING);
}

int OfficialRecoveryMarker_IsPending(
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],unsigned profile)
{
    OfficialRecoveryRecord saved;
    unsigned savedProfile=0,flags=0;
    if (profile<1u || profile>8u) return 0;
    if (!OfficialRecoveryMarker_Decode(marker,&saved,&savedProfile,&flags)) return 0;
    (void)saved;
    return savedProfile==profile &&
        (flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_PENDING)!=0u &&
        (flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED)==0u;
}

int OfficialRecoveryMarker_BindTransaction(
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    const OfficialRecoveryRecord *server,unsigned profile)
{
    if (!server || !OfficialRecoveryMarker_IsPending(marker,profile)) return 0;
    return OfficialRecoveryMarker_Encode(marker,server,profile,
        OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED);
}

int OfficialRecoveryMarker_MatchesServer(
    const unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE],
    const OfficialRecoveryRecord *server,unsigned profile)
{
    OfficialRecoveryRecord saved;
    unsigned savedProfile=0,flags=0;
    if (!server || !OfficialRecoveryMarker_Decode(marker,&saved,&savedProfile,&flags)) return 0;
    if ((flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED)==0u) return 0;
    if ((flags&OFFICIAL_RECOVERY_MARKER_FLAG_BULK_PENDING)!=0u) return 0;
    if (savedProfile!=profile) return 0;
    return saved.dataId==server->dataId &&
        saved.transactionPassword==server->transactionPassword &&
        saved.curVersion==server->curVersion &&
        saved.updateVersion==server->updateVersion &&
        saved.size==server->size;
}
