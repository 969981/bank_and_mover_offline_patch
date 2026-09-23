#include "official_recovery_marker_io.h"

int OfficialRecoveryMarkerIO_ValidateImage(const unsigned char *image,unsigned size)
{
    OfficialRecoveryRecord record;
    return image && size==OFFICIAL_RECOVERY_MARKER_SIZE &&
        OfficialRecoveryMarker_Decode(image,&record,0,0);
}

void OfficialRecoveryMarkerIO_Invalidate(
    unsigned char image[OFFICIAL_RECOVERY_MARKER_SIZE])
{
    unsigned i;
    if (!image) return;
    for (i=0;i<OFFICIAL_RECOVERY_MARKER_SIZE;i++) image[i]=0;
}

int OfficialRecoveryMarkerIO_IsEmpty(
    const unsigned char image[OFFICIAL_RECOVERY_MARKER_SIZE])
{
    unsigned i;
    if (!image) return 1;
    for (i=0;i<OFFICIAL_RECOVERY_MARKER_SIZE;i++) if (image[i]) return 0;
    return 1;
}
