/* Route A V0 bulk-import wrapper for Pokemon Bank v1.5 Offline Mode. */
/* Route A V0：仅把 bulk_import.bin 的 100 个主 Bank Box 覆盖到运行时对象。 */
#include "bulk_import.h"

typedef unsigned char u8;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long long u64;

enum {
    ARCHIVE_SDMC = 9,
    PATH_EMPTY = 1,
    PATH_ASCII = 3,
    OPEN_READ = 1
};

#define FSUSER_HANDLE ((volatile u32 *)0x00390100u)
#define OPEN_DIRECT ((OpenDirect)0x0022D338u)
#define FILE_READ ((FileRead)0x001658C8u)
#define FILE_CLOSE ((FileClose)0x00165920u)
#define FILE_GET_SIZE ((FileGetSize)0x001659ACu)

typedef s32 (*OpenDirect)(volatile u32 *, u32 *, u32, u32, u32, const void *, u32,
    u32, const void *, u32, u32, u32);
typedef s32 (*FileRead)(u32 *, u32 *, u64, void *, u32);
typedef s32 (*FileClose)(u32 *);
typedef s32 (*FileGetSize)(u32 *, u64 *);

static const char emptyPath[1] = {0};
static const char bulkImportPath[] = "/3ds/Bank/bulk_import.bin";

/* patch.c is compiled with a preprocessor rename so this symbol remains the
   proven local bankdata loader. */
extern int OfflinePatch_LoadBankData_Base(u8 *state);

static s32 openFile(const char *path,u32 pathSize,u32 flags,u32 *handle)
{
    return OPEN_DIRECT(FSUSER_HANDLE,handle,0,ARCHIVE_SDMC,PATH_EMPTY,emptyPath,1,
        PATH_ASCII,path,pathSize,flags,0);
}

/* Returns 1 when applied, 0 when no valid bulk image should be applied,
   and -1 only when a box-range read may have partially modified runtime. */
static int applyBulkMainBoxes(u8 *runtimeBody)
{
    u8 header[4];
    u32 handle=0,readCount=0;
    u64 size=0;
    s32 result,closeResult=0;

    result=openFile(bulkImportPath,sizeof(bulkImportPath),OPEN_READ,&handle);
    if (result) return 0;

    result=FILE_GET_SIZE(&handle,&size);
    if (!result && size==BANK_V15_SIZE)
        result=FILE_READ(&handle,&readCount,BANK_V15_VERSION_OFFSET,header,sizeof(header));
    else if (!result)
        result=-1;

    if (result || readCount!=sizeof(header) || !BankBulk_ValidateHeader4(header)) {
        if (handle) (void)FILE_CLOSE(&handle);
        return 0;
    }

    readCount=0;
    result=FILE_READ(&handle,&readCount,BANK_V15_MAIN_BOX_START,
        runtimeBody+BANK_V15_MAIN_BOX_START,BANK_V15_MAIN_BOX_SIZE);
    if (handle) closeResult=FILE_CLOSE(&handle);

    if (!result && !closeResult && readCount==BANK_V15_MAIN_BOX_SIZE) return 1;
    return -1;
}

__attribute__((used,noinline,section(".text.offline")))
int OfflinePatch_LoadBankData(u8 *state)
{
    u8 *flow,*object;
    int applyResult;

    if (!OfflinePatch_LoadBankData_Base(state)) return 0;

    flow=*(u8 **)(state+8);
    object=flow?*(u8 **)(flow+0xCC):0;
    if (!object || *(u32 *)object!=0x003626FCu) return 0;

    applyResult=applyBulkMainBoxes(object+8);
    if (applyResult>=0) return 1;

    /* A failed/short main-box read might already have touched runtime. Reload
       the proven bankdata.bin path to make the operation atomic from the UI's
       point of view. */
    return OfflinePatch_LoadBankData_Base(state);
}
