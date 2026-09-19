#ifndef BANK_OFFICIAL_BULK_SYNC_H
#define BANK_OFFICIAL_BULK_SYNC_H

#define BANK_V15_SIZE 0xBB518u
#define BANK_G7_PKHEX_VIEW_SIZE 0xACA48u
#define BANK_V15_VERSION_OFFSET 0x15Cu
#define BANK_V15_BOX_COUNT_OFFSET 0x15Eu
#define BANK_V15_MAIN_BOX_START 0x17Cu
#define BANK_V15_MAIN_BOX_END 0xAAF14u
#define BANK_V15_BOX_COUNT 100u
#define BANK_V15_SLOTS_PER_BOX 30u
#define BANK_V15_PKM_SIZE 0xE8u
#define BANK_V15_BOX_PKM_BYTES (BANK_V15_SLOTS_PER_BOX*BANK_V15_PKM_SIZE)
#define BANK_V15_BOX_META_SIZE 0x26u
#define BANK_V15_BOX_STRIDE 0x1B56u
#define BANK_V15_TAG_START 0xACA44u
#define BANK_V15_SOURCE_START 0xB4AA0u
#define BANK_V15_TIMESTAMP_START 0xB5658u

#ifdef OFFICIAL_BULK_INTERNAL
#define OFFICIAL_BULK_API static
#else
#define OFFICIAL_BULK_API
#endif

typedef struct {
    unsigned char formatTag;
    unsigned char sourceSoftware;
    unsigned long long timestamp;
} OfficialBulkMetadata;

OFFICIAL_BULK_API int OfficialBulk_IsSupportedSize(unsigned long long size);
OFFICIAL_BULK_API int OfficialBulk_ValidateHeader4(const unsigned char header[4]);
OFFICIAL_BULK_API int OfficialBulk_RecordIsEmpty(const unsigned char record[BANK_V15_PKM_SIZE]);
OFFICIAL_BULK_API int OfficialBulk_MergeSlot(unsigned char *runtimeBody,unsigned box,unsigned slot,
    const unsigned char bulkRecord[BANK_V15_PKM_SIZE],const OfficialBulkMetadata *meta);
OFFICIAL_BULK_API void OfficialBulk_CopyBoxMetadata(unsigned char *runtimeBody,unsigned box,
    const unsigned char bulkMeta[BANK_V15_BOX_META_SIZE]);
#ifndef OFFICIAL_BULK_RUNTIME
OFFICIAL_BULK_API int OfficialBulk_ApplyDataOnly(unsigned char *runtimeBody,const unsigned char *bulkBody,
    unsigned long long bulkSize,const OfficialBulkMetadata *meta);
#endif
OFFICIAL_BULK_API int OfficialBulk_BuildBackupPath(const unsigned char *runtimeBody,char *out,unsigned outSize);
OFFICIAL_BULK_API unsigned char OfficialBulk_FormatTagForProfile(unsigned profileId);
OFFICIAL_BULK_API int OfficialBulk_ShouldProcessState(unsigned substate,unsigned callbackStatus,unsigned specialFlag);

#endif
