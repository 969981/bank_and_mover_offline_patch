#include "official_bulk_sync.h"

typedef unsigned char u8;
typedef unsigned short u16;
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
#define STAGE_FILE_UPDATE ((StageFileUpdate)0x002A2504u)
#define COMPLETE_UPDATE ((TransactionUpdate)0x001D5D74u)
#define GAME_REGISTRY_SLOT ((volatile u32 *)0x003AB90Cu)
#define BANK_ROOT_SLOT ((volatile u32 *)0x003AB938u)
#define HOME_BULK_DIRTY ((volatile u8 *)0x003ABFFCu)
#define BANK_OBJECT_VTABLE 0x003626FCu
#define BANK_V15_HEADER_WORD 0x00640002u

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
typedef int (*StageFileUpdate)(void *,void *,u32,void *);
typedef int (*TransactionUpdate)(void *,void *,u32);

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

/* The restore source is the exact snapshot written and verified immediately before apply. */
static int restoreSnapshot(const char *path,u32 pathSize,u8 *body)
{
    u32 h=0,n=0; s32 r;
    r=openFile(path,pathSize,OPEN_READ,&h);
    if (!r) r=FILE_READ(&h,&n,0,body,BANK_V15_SIZE);
    if (h) (void)FILE_CLOSE(&h);
    return !r && n==BANK_V15_SIZE;
}

static u8 *bankObjectFromState(u8 *state)
{
    u8 *flow,*object;
    flow=*(u8 **)(state+8);
    object=flow?*(u8 **)(flow+0xCC):0;
    return object && *(u32 *)object==BANK_OBJECT_VTABLE?object:0;
}

static int queryMetadata(OfficialBulkMetadata *meta)
{
    u8 *registry,*model,*sourceObject,*root;
    u32 *vtable,stamp[2]; unsigned profile; SourceSoftwareGetter getSource;
    registry=(u8 *)(*GAME_REGISTRY_SLOT); root=(u8 *)(*BANK_ROOT_SLOT);
    if (!registry || !root) return 0;
    model=(u8 *)GAME_MODEL_ACTIVE(*(void **)(registry+0x1C));
    if (!model) return 0;
    profile=model[8]; meta->formatTag=OfficialBulk_FormatTagForProfile(profile);
    if (meta->formatTag==0xFFu) return 0;
    sourceObject=model+((profile>=5u)?0x74304u:0x129ACu);
    vtable=*(u32 **)sourceObject; if (!vtable || !vtable[3]) return 0;
    getSource=(SourceSoftwareGetter)vtable[3]; meta->sourceSoftware=getSource(sourceObject);
    TIME_CONTAINER_INIT(stamp);
    if (!TIME_QUERY(*(void **)(root+0x138),stamp)) return 0;
    meta->timestamp=TIME_PACK(stamp); return 1;
}

static int readExact(u32 *handle,u64 offset,void *dst,u32 size)
{
    u32 n=0; return !FILE_READ(handle,&n,offset,dst,size) && n==size;
}

static int applyBulkFile(u8 *body,const OfficialBulkMetadata *meta)
{
    u32 header=0,h=0,box,slot; u8 record[BANK_V15_PKM_SIZE],boxMeta[BANK_V15_BOX_META_SIZE];
    u64 size=0,offset; s32 r,closeResult=0;
    r=openFile(bulkPath,sizeof(bulkPath),OPEN_READ,&h);
    if (r) return 0;
    r=FILE_GET_SIZE(&h,&size);
    if (r || !OfficialBulk_IsSupportedSize(size) ||
        !readExact(&h,BANK_V15_VERSION_OFFSET,&header,sizeof(header)) || header!=BANK_V15_HEADER_WORD) {
        if (h) (void)FILE_CLOSE(&h);
        return 0;
    }
    for (box=0;box<BANK_V15_BOX_COUNT;box++) {
        offset=BANK_V15_MAIN_BOX_START+(u64)box*BANK_V15_BOX_STRIDE;
        for (slot=0;slot<BANK_V15_SLOTS_PER_BOX;slot++) {
            if (!readExact(&h,offset+(u64)slot*BANK_V15_PKM_SIZE,record,sizeof(record)) ||
                !OfficialBulk_MergeSlot(body,box,slot,record,meta)) { (void)FILE_CLOSE(&h); return -1; }
        }
        if (!readExact(&h,offset+BANK_V15_BOX_PKM_BYTES,boxMeta,sizeof(boxMeta))) { (void)FILE_CLOSE(&h); return -1; }
        OfficialBulk_CopyBoxMetadata(body,box,boxMeta);
    }
    if (h) closeResult=FILE_CLOSE(&h);
    return closeResult?-1:1;
}

static __attribute__((noinline)) void fallbackHomeRollback(u8 *state)
{
    *(u16 *)(state+0x40)=0; *HOME_BULK_DIRTY=2; *(u32 *)(state+0x10)=1u;
}

__attribute__((used,noinline,section(".text.official")))
int OfficialBulkHomeCommit_Process(void *stateVoid)
{
    u8 *state=(u8 *)stateVoid,*object; u32 substate;
    if (!*HOME_BULK_DIRTY) return 0;
    substate=*(u32 *)(state+0x10);
    if (*HOME_BULK_DIRTY==2u) {
        if (substate==2u && state[0x40]) {
            *HOME_BULK_DIRTY=0; *(u16 *)(state+0x40)=0; *(u32 *)(state+0x10)=4u; return 1;
        }
        return 0;
    }
    if (substate==0u) return 0;
    if (substate==1u) {
        object=bankObjectFromState(state);
        if (!object) { fallbackHomeRollback(state); return 1; }
        *(u16 *)(state+0x40)=0;
        if (!STAGE_FILE_UPDATE(*(void **)(state+0x3C),object+8,BANK_V15_SIZE,*(void **)(state+0x28))) {
            fallbackHomeRollback(state); return 1;
        }
        *(u32 *)(state+0x10)=0x80u; return 1;
    }
    if (substate==0x80u) {
        if (!state[0x40]) return 1;
        if (state[0x41]) { fallbackHomeRollback(state); return 1; }
        *(u16 *)(state+0x40)=0;
        if (!COMPLETE_UPDATE(*(void **)(state+0x3C),*(void **)(state+0x28),0u)) {
            fallbackHomeRollback(state); return 1;
        }
        *(u32 *)(state+0x10)=0x81u; return 1;
    }
    if (substate==0x81u) {
        if (!state[0x40]) return 1;
        if (state[0x41]) { fallbackHomeRollback(state); return 1; }
        *HOME_BULK_DIRTY=0; *(u16 *)(state+0x40)=0; *(u32 *)(state+0x10)=3u; return 1;
    }
    fallbackHomeRollback(state); return 1;
}

__attribute__((used,noinline,section(".text.official")))
int OfficialBulkSync_Process(void *stateVoid,volatile u32 *commandBuffer)
{
    u8 *state=(u8 *)stateVoid,*object,*body; OfficialBulkMetadata meta={0u,0u,0u};
    char backupPath[48]; int applyResult,mode;
    mode=OfficialBulk_ShouldProcessState(*(u32 *)(state+0x10),state[0x40],state[0x41]);
    if (!mode) return 0;
    if (mode==2) *HOME_BULK_DIRTY=0;
    object=bankObjectFromState(state); if (!object) return 0; body=object+8;
    if (*(const u32 *)(body+BANK_V15_VERSION_OFFSET)!=BANK_V15_HEADER_WORD) return 0;
    if (mode==1 && !queryMetadata(&meta)) return 0;
    if (!OfficialBulk_BuildBackupPath(body,backupPath,sizeof(backupPath)) ||
        !writeSnapshot(backupPath,39u,body,commandBuffer)) return 0;
    applyResult=applyBulkFile(body,(mode==2)?0:&meta);
    if (applyResult<0) { (void)restoreSnapshot(backupPath,39u,body); return 0; }
    if (applyResult>0 && mode==2) *HOME_BULK_DIRTY=1;
    return applyResult>0;
}
