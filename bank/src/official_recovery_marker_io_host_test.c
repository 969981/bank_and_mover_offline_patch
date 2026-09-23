#include <assert.h>
#include <string.h>
#include "official_recovery_marker_io.h"

int main(void)
{
    unsigned char marker[OFFICIAL_RECOVERY_MARKER_SIZE];
    unsigned char corrupt[OFFICIAL_RECOVERY_MARKER_SIZE];
    OfficialRecoveryRecord server={0};
    server.dataId=1u;
    server.transactionPassword=2u;
    server.curVersion=3u;
    server.updateVersion=4u;
    server.size=0xBB518u;

    assert(strcmp(OFFICIAL_RECOVERY_MARKER_PATH,
        "/3ds/Bank/official_bulk_recovery.bin")==0);
    assert(OfficialRecoveryMarker_EncodePending(marker,7u));
    assert(OfficialRecoveryMarkerIO_ValidateImage(marker,
        OFFICIAL_RECOVERY_MARKER_SIZE));
    assert(!OfficialRecoveryMarkerIO_ValidateImage(marker,
        OFFICIAL_RECOVERY_MARKER_SIZE-1u));

    memcpy(corrupt,marker,sizeof(marker));
    corrupt[20]^=1u;
    assert(!OfficialRecoveryMarkerIO_ValidateImage(corrupt,
        OFFICIAL_RECOVERY_MARKER_SIZE));

    OfficialRecoveryMarkerIO_Invalidate(marker);
    assert(OfficialRecoveryMarkerIO_IsEmpty(marker));
    assert(!OfficialRecoveryMarkerIO_ValidateImage(marker,
        OFFICIAL_RECOVERY_MARKER_SIZE));

    assert(OfficialRecoveryMarker_EncodePending(marker,7u));
    assert(OfficialRecoveryMarker_BindTransaction(marker,&server,7u));
    assert(OfficialRecoveryMarkerIO_ValidateImage(marker,
        OFFICIAL_RECOVERY_MARKER_SIZE));
    return 0;
}
