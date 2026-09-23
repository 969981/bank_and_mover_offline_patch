#ifndef BANK_OFFICIAL_RECOVERY_MARKER_IO_H
#define BANK_OFFICIAL_RECOVERY_MARKER_IO_H

#include "official_recovery_marker.h"

#define OFFICIAL_RECOVERY_MARKER_PATH "/3ds/Bank/official_bulk_recovery.bin"

int OfficialRecoveryMarkerIO_ValidateImage(const unsigned char *image,unsigned size);
void OfficialRecoveryMarkerIO_Invalidate(
    unsigned char image[OFFICIAL_RECOVERY_MARKER_SIZE]);
int OfficialRecoveryMarkerIO_IsEmpty(
    const unsigned char image[OFFICIAL_RECOVERY_MARKER_SIZE]);

#endif
