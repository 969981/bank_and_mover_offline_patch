#include "official_bulk_sync.h"

static unsigned char *runtimeSlot(unsigned char *body,unsigned box,unsigned slot)
{
    return body+BANK_V15_MAIN_BOX_START+box*BANK_V15_BOX_STRIDE+slot*BANK_V15_PKM_SIZE;
}

static void writeU64LE(unsigned char *p,unsigned long long v)
{
    unsigned i;
    for (i=0;i<8u;i++) { p[i]=(unsigned char)v; v>>=8; }
}

OFFICIAL_BULK_API int OfficialBulk_IsSupportedSize(unsigned long long size)
{
    return size==BANK_V15_SIZE || size==BANK_G7_PKHEX_VIEW_SIZE;
}

OFFICIAL_BULK_API int OfficialBulk_ValidateHeader4(const unsigned char header[4])
{
    unsigned version=(unsigned)header[0]|((unsigned)header[1]<<8);
    unsigned boxes=(unsigned)header[2]|((unsigned)header[3]<<8);
    return version==2u && boxes==100u;
}

OFFICIAL_BULK_API int OfficialBulk_RecordIsEmpty(const unsigned char record[BANK_V15_PKM_SIZE])
{
    unsigned i;
    for (i=0;i<BANK_V15_PKM_SIZE;i++) if (record[i]) return 0;
    return 1;
}

OFFICIAL_BULK_API int OfficialBulk_MergeSlot(unsigned char *runtimeBody,unsigned box,unsigned slot,
    const unsigned char bulkRecord[BANK_V15_PKM_SIZE],const OfficialBulkMetadata *meta)
{
    unsigned char *dst;
    unsigned i,index;
    int changed=0;
    if (!runtimeBody || !bulkRecord || box>=BANK_V15_BOX_COUNT ||
        slot>=BANK_V15_SLOTS_PER_BOX) return 0;
    dst=runtimeSlot(runtimeBody,box,slot);
    for (i=0;i<BANK_V15_PKM_SIZE;i++) if (dst[i]!=bulkRecord[i]) { changed=1; break; }
    if (!changed) return 1;
    for (i=0;i<BANK_V15_PKM_SIZE;i++) dst[i]=bulkRecord[i];
    if (OfficialBulk_RecordIsEmpty(bulkRecord)) return 1;
    index=box*BANK_V15_SLOTS_PER_BOX+slot;
    if (!meta) {
        /* HOME direct consumes PKHeX Bank7/PK7 canonical payload. There is no
           selected Gen6/7 game, so only the format tag is authoritative here;
           source/timestamp stay exactly as downloaded from the fresh server. */
        runtimeBody[BANK_V15_TAG_START+index]=1u;
        return 1;
    }
    runtimeBody[BANK_V15_TAG_START+index]=meta->formatTag;
    runtimeBody[BANK_V15_SOURCE_START+index]=meta->sourceSoftware;
    writeU64LE(runtimeBody+BANK_V15_TIMESTAMP_START+index*8u,meta->timestamp);
    return 1;
}

OFFICIAL_BULK_API void OfficialBulk_CopyBoxMetadata(unsigned char *runtimeBody,unsigned box,
    const unsigned char bulkMeta[BANK_V15_BOX_META_SIZE])
{
    unsigned i;
    unsigned char *dst;
    if (!runtimeBody || !bulkMeta || box>=BANK_V15_BOX_COUNT) return;
    dst=runtimeBody+BANK_V15_MAIN_BOX_START+box*BANK_V15_BOX_STRIDE+BANK_V15_BOX_PKM_BYTES;
    for (i=0;i<BANK_V15_BOX_META_SIZE;i++) dst[i]=bulkMeta[i];
}

#ifndef OFFICIAL_BULK_RUNTIME
OFFICIAL_BULK_API int OfficialBulk_ApplyDataOnly(unsigned char *runtimeBody,const unsigned char *bulkBody,
    unsigned long long bulkSize,const OfficialBulkMetadata *meta)
{
    unsigned box,slot;
    const unsigned char *src;
    if (!runtimeBody || !bulkBody || !OfficialBulk_IsSupportedSize(bulkSize)) return 0;
    if (!OfficialBulk_ValidateHeader4(bulkBody+BANK_V15_VERSION_OFFSET)) return 0;
    for (box=0;box<BANK_V15_BOX_COUNT;box++) {
        src=bulkBody+BANK_V15_MAIN_BOX_START+box*BANK_V15_BOX_STRIDE;
        for (slot=0;slot<BANK_V15_SLOTS_PER_BOX;slot++) {
            if (!OfficialBulk_MergeSlot(runtimeBody,box,slot,
                src+slot*BANK_V15_PKM_SIZE,meta)) return 0;
        }
        OfficialBulk_CopyBoxMetadata(runtimeBody,box,src+BANK_V15_BOX_PKM_BYTES);
    }
    return 1;
}
#endif

static char digit(unsigned value) { return (char)('0'+value); }
static unsigned takeDigit(unsigned *value,unsigned place)
{
    unsigned d=0;
    while (*value>=place) { *value-=place; d++; }
    return d;
}
static void put2(char *p,unsigned value)
{
    p[0]=digit(takeDigit(&value,10u)); p[1]=digit(value);
}
static void put4(char *p,unsigned value)
{
    p[0]=digit(takeDigit(&value,1000u));
    p[1]=digit(takeDigit(&value,100u));
    p[2]=digit(takeDigit(&value,10u));
    p[3]=digit(value);
}

OFFICIAL_BULK_API int OfficialBulk_BuildBackupPath(const unsigned char *runtimeBody,char *out,unsigned outSize)
{
    static const char prefix[]="/3ds/Bank/bankdata_";
    static const char suffix[]=".bin";
    unsigned i,pos=0,year,month,day,hour,minute,second;
    if (!runtimeBody || !out || outSize<39u) return 0;
    year=(unsigned)runtimeBody[0x160]|((unsigned)runtimeBody[0x161]<<8);
    month=runtimeBody[0x162]; day=runtimeBody[0x163]; hour=runtimeBody[0x164];
    minute=runtimeBody[0x165]; second=runtimeBody[0x166];
    if (year>9999u || month<1u || month>12u || day<1u || day>31u ||
        hour>23u || minute>59u || second>59u) return 0;
    for (i=0;i<sizeof(prefix)-1u;i++) out[pos++]=prefix[i];
    put4(out+pos,year); pos+=4; put2(out+pos,month); pos+=2; put2(out+pos,day); pos+=2;
    out[pos++]='_'; put2(out+pos,hour); pos+=2; put2(out+pos,minute); pos+=2; put2(out+pos,second); pos+=2;
    for (i=0;i<sizeof(suffix);i++) out[pos++]=suffix[i];
    return 1;
}

OFFICIAL_BULK_API unsigned char OfficialBulk_FormatTagForProfile(unsigned profileId)
{
    if (profileId>=1u && profileId<=4u) return 0u;
    if (profileId>=5u && profileId<=8u) return 1u;
    return 0xFFu;
}

OFFICIAL_BULK_API int OfficialBulk_ShouldProcessState(unsigned substate,unsigned callbackStatus,unsigned specialFlag)
{
    return substate==2u && callbackStatus==1u && specialFlag<=1u;
}
