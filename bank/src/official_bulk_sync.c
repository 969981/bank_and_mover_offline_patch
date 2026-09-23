#include "official_bulk_sync.h"

typedef unsigned char u8;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long long u64;

enum { ARCHIVE_SDMC=9, PATH_EMPTY=1, PATH_ASCII=3, OPEN_READ=1, OPEN_WRITE=2, OPEN_CREATE=4, WRITE_FLUSH=1 };

#define FSUSER_HANDLE ((volatile u32 *)0x00390100u)
#define OPEN_DIRECT ((OpenDirect)0x0022D338u)
#define FILE_READ ((FileRead)0x001658C8u)
#define FILE_CLOSE ((FileClose)0x00165920u)
#define FILE_WRITE ((FileWrite)0x0016594Cu)
#define FILE_GET_SIZE ((FileGetSize)0x001659ACu)
#define GAME_MODEL_ACTIVE ((GameModelActive)0x00233A6Cu)
#define TIME_CONTAINER_INIT ((TimeContainerInit)0x00234648u)
#define TIME_QUERY ((TimeQuery)0x001D3BF4u)
#define TIME_PACK ((TimePack)0x001F2BD4u)
#define GAME_REGISTRY_SLOT ((volatile u32 *)0x003AB90Cu)
#define BANK_ROOT_SLOT ((volatile u32 *)0x003AB938u)
#define RECOVERY_SESSION_FLAG ((volatile u8 *)0x003ABFFCu)
#define BANK_OBJECT_VTABLE 0x003626FCu

typedef s32 (*OpenDirect)(volatile u32 *,u32 *,u32,u32,u32,const void *,u32,u32,const void *,u32,u32,u32);
typedef s32 (*FileRead)(u32 *,u32 *,u64,void *,u32);
typedef s32 (*FileWrite)(u32 *,u32 *,u64,const void *,u32,u32);
typedef s32 (*FileClose)(u32 *);
typedef s32 (*FileGetSize)(u32 *,u64 *);
typedef void *(*GameModelActive)(void *);
typedef void (*TimeContainerInit)(void *);
typedef int (*TimeQuery)(void *,void *);
typedef u64 (*TimePack)(void *);
typedef u8 (*SourceSoftwareGetter)(void *);

static const char emptyPath[1]={0};
static const char bulkPath[]="/3ds/Bank/bulk_import.bin";

static s32 sync(u32 handle)
{
    register u32 r0 __asm__("r0")=handle;
    __asm__ volatile("svc 0x32" : "+r"(r0) : : "r1","r2","r3","r12","memory","cc");
    return (s32)r0;
}

static s32 setSize(u32 handle,u64 size,volatile u32 *c)
{
    s32 r;
    c[0]=0x08050080u; c[1]=(u32)size; c[2]=(u32)(size>>32);
    r=sync(handle); return r?r:(s32)c[1];
}

static s32 openFile(const char *path,u32 pathSize,u32 flags,u32 *handle)
{
    return OPEN_DIRECT(FSUSER_HANDLE,handle,0,ARCHIVE_SDMC,PATH_EMPTY,emptyPath,1,
        PATH_ASCII,path,pathSize,flags,0);
}

static int writeSnapshot(const char *path,u32 pathSize,const u8 *body,volatile u32 *commandBuffer)
{
    u32 h=0,n=0; s32 r,closeResult=0;
    r=openFile(path,pathSize,OPEN_READ|OPEN_WRITE|OPEN_CREATE,&h);
    if (!r) r=setSize(h,BANK_V15_SIZE,commandBuffer);
    if (!r) r=FILE_WRITE(&h,&n,0,body,BANK_V15_SIZE,WRITE_FLUSH);
    if (h) closeResult=FILE_CLOSE(&h);
    return !r && !closeResult && n==BANK_V15_SIZE;
}

static int restoreSnapshot(const char *path,u32 pathSize,u8 *body)
{
    u32 h=0,n=0; u64 size=0; s32 r,closeResult=0;
    r=openFile(path,pathSize,OPEN_READ,&h);
    if (!r) r=FILE_GET_SIZE(&h,&size);
    if (!r && size==BANK_V15_SIZE) r=FILE_READ(&h,&n,0,body,BANK_V15_SIZE);
    else if (!r) r=-1;
    if (h) closeResult=FILE_CLOSE(&h);
    return !r && !closeResult && n==BANK_V15_SIZE &&
        OfficialBulk_ValidateHeader4(body+BANK_V15_VERSION_OFFSET);
}

static int queryMetadata(OfficialBulkMetadata *meta)
{
    u8 *registry,*model,*sourceObject,*root;
    u32 *vtable;
    u32 stamp[2];
    unsigned profile;
    SourceSoftwareGetter getSource;

    registry=(u8 *)(*GAME_REGISTRY_SLOT);
    root=(u8 *)(*BANK_ROOT_SLOT);
    if (!registry || !root) return 0;
    model=(u8 *)GAME_MODEL_ACTIVE(*(void **)(registry+0x1C));
    if (!model) return 0;
    profile=model[8];
    meta->formatTag=OfficialBulk_FormatTagForProfile(profile);
    if (meta->formatTag==0xFFu) return 0;
    sourceObject=model+((profile>=5u)?0x74304u:0x129ACu);
    vtable=*(u32 **)sourceObject;
    if (!vtable || !vtable[3]) return 0;
    getSource=(SourceSoftwareGetter)vtable[3];
    meta->sourceSoftware=getSource(sourceObject);
    TIME_CONTAINER_INIT(stamp);
    if (!TIME_QUERY(*(void **)(root+0x138),stamp)) return 0;
    meta->timestamp=TIME_PACK(stamp);
    return 1;
}

static int readExact(u32 *handle,u64 offset,void *dst,u32 size)
{
    u32 n=0;
    return !FILE_READ(handle,&n,offset,dst,size) && n==size;
}

/* 1=applied, 0=no valid bulk input, -1=runtime may be partially modified. */
static int applyBulkFile(u8 *body,const OfficialBulkMetadata *meta)
{
    u8 header[4],record[BANK_V15_PKM_SIZE],boxMeta[BANK_V15_BOX_META_SIZE];
    u32 h=0,box,slot; u64 size=0,offset; s32 r,closeResult=0;
    r=openFile(bulkPath,sizeof(bulkPath),OPEN_READ,&h);
    if (r) return 0;
    r=FILE_GET_SIZE(&h,&size);
    if (r || !OfficialBulk_IsSupportedSize(size) ||
        !readExact(&h,BANK_V15_VERSION_OFFSET,header,sizeof(header)) ||
        !OfficialBulk_ValidateHeader4(header)) {
        if (h) (void)FILE_CLOSE(&h);
        return 0;
    }
    for (box=0;box<BANK_V15_BOX_COUNT;box++) {
        offset=BANK_V15_MAIN_BOX_START+(u64)box*BANK_V15_BOX_STRIDE;
        for (slot=0;slot<BANK_V15_SLOTS_PER_BOX;slot++) {
            if (!readExact(&h,offset+(u64)slot*BANK_V15_PKM_SIZE,record,sizeof(record))) {
                (void)FILE_CLOSE(&h); return -1;
            }
            if (!OfficialBulk_MergeSlot(body,box,slot,record,meta)) {
                (void)FILE_CLOSE(&h); return -1;
            }
        }
        if (!readExact(&h,offset+BANK_V15_BOX_PKM_BYTES,boxMeta,sizeof(boxMeta))) {
            (void)FILE_CLOSE(&h); return -1;
        }
        OfficialBulk_CopyBoxMetadata(body,box,boxMeta);
    }
    if (h) closeResult=FILE_CLOSE(&h);
    return closeResult?-1:1;
}

__attribute__((used,noinline,section(".text.official")))
int OfficialBulkSync_Process(void *stateVoid,volatile u32 *commandBuffer)
{
    u8 *state=(u8 *)stateVoid,*flow,*object,*body;
    OfficialBulkMetadata meta={0u,0u,0u};
    char backupPath[48];
    unsigned substate;
    int applyResult,haveMeta;

    if (!state || !commandBuffer) return 0;
    substate=*(u32 *)(state+0x10);
    if (substate==0u) *RECOVERY_SESSION_FLAG=0u;
    if (!OfficialBulk_ShouldProcessState(substate,state[0x40],state[0x41])) return 0;
    flow=*(u8 **)(state+8);
    object=flow?*(u8 **)(flow+0xCC):0;
    if (!object || *(u32 *)object!=BANK_OBJECT_VTABLE) return 0;
    body=object+8;
    if (!OfficialBulk_ValidateHeader4(body+BANK_V15_VERSION_OFFSET)) return 0;
    haveMeta=queryMetadata(&meta);
    if (!OfficialBulk_BuildBackupPath(body,backupPath,sizeof(backupPath))) return 0;
    if (!writeSnapshot(backupPath,39u,body,commandBuffer)) return 0;
    if (!haveMeta) return 0;

    applyResult=applyBulkFile(body,&meta);
    if (applyResult<0) {
        (void)restoreSnapshot(backupPath,39u,body);
        return 0;
    }
    if (applyResult>0) {
        *RECOVERY_SESSION_FLAG=1u;
        return 1;
    }
    return 0;
}
