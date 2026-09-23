#include <assert.h>
#include <string.h>
#include "official_recovery_marker.h"

static OfficialRecoveryRecord tx(void)
{
    OfficialRecoveryRecord r;
    memset(&r,0,sizeof(r));
    r.dataId=0x1122334455667788ULL;
    r.transactionPassword=0x8877665544332211ULL;
    r.curVersion=41u;
    r.updateVersion=42u;
    r.size=0xBB518u;
    r.status=2u;
    return r;
}

int main(void)
{
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE];
    unsigned char corrupt[OFFICIAL_RECOVERY_MARKER_SIZE];
    OfficialRecoveryRecord server=tx(),decoded;
    unsigned profile=0,flags=0;

    assert(OfficialRecoveryMarker_Encode(marker,&server,7u,
        OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED)==1);
    assert(OfficialRecoveryMarker_Decode(marker,&decoded,&profile,&flags)==1);
    assert(profile==7u);
    assert(flags==OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED);
    assert(decoded.dataId==server.dataId);
    assert(decoded.transactionPassword==server.transactionPassword);
    assert(decoded.curVersion==server.curVersion);
    assert(decoded.updateVersion==server.updateVersion);
    assert(decoded.size==server.size);

    assert(OfficialRecoveryMarker_MatchesServer(marker,&server,7u)==1);

    server.curVersion++;
    assert(OfficialRecoveryMarker_MatchesServer(marker,&server,7u)==0);
    server.curVersion--;
    server.transactionPassword^=1ULL;
    assert(OfficialRecoveryMarker_MatchesServer(marker,&server,7u)==0);
    server.transactionPassword^=1ULL;
    assert(OfficialRecoveryMarker_MatchesServer(marker,&server,6u)==0);

    memcpy(corrupt,marker,sizeof(marker));
    corrupt[20]^=0x80u;
    assert(OfficialRecoveryMarker_Decode(corrupt,&decoded,&profile,&flags)==0);

    memcpy(corrupt,marker,sizeof(marker));
    corrupt[6]=0;
    corrupt[7]=0;
    OfficialRecoveryMarker_Rechecksum(corrupt);
    assert(OfficialRecoveryMarker_MatchesServer(corrupt,&server,7u)==0);

    assert(OfficialRecoveryMarker_Encode(marker,&server,0u,
        OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED)==0);
    assert(OfficialRecoveryMarker_Encode(marker,&server,9u,
        OFFICIAL_RECOVERY_MARKER_FLAG_BULK_APPLIED)==0);
    return 0;
}
