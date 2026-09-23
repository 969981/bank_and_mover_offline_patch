/* Minimal production runtime for Variant B.
 * Included after official_bulk_sync.c so the existing SDMC/file helpers and
 * game-profile runtime symbols are shared instead of duplicated.
 */

typedef struct {
    u8 bytes[48];
} SmartMarker;

#define SMART_MARKER_VERSION 2u
#define SMART_FLAG_BOUND 0x0001u
#define SMART_FLAG_PENDING 0x0002u
#define SMART_STAGE_BULK_APPLIED 1u
#define SMART_STAGE_GAME_SAVE_STARTED 3u
#define SMART_STAGE_GAME_SAVE_OK 4u
#define SM_OFF_VERSION 4u
#define SM_OFF_FLAGS 6u
#define SM_OFF_PROFILE 8u
#define SM_OFF_STAGE 9u
#define SM_OFF_DATA_ID 12u
#define SM_OFF_PASSWORD 20u
#define SM_OFF_CUR 28u
#define SM_OFF_UPDATE 32u
#define SM_OFF_SIZE 36u
#define SM_OFF_CHECKSUM 44u

static const char smartMarkerPath[]="/3ds/Bank/official_bulk_recovery.bin";

static u32 smGet32(const u8 *p)
{
    return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);
}
static void smPut32(u8 *p,u32 v)
{
    p[0]=(u8)v; p[1]=(u8)(v>>8); p[2]=(u8)(v>>16); p[3]=(u8)(v>>24);
}
static u32 smChecksum(const u8 *p)
{
    u32 i,h=2166136261u;
    for (i=0;i<44u;i++) { h^=p[i]; h*=16777619u; }
    return h;
}
static int smWrite(const SmartMarker *m,volatile u32 *commandBuffer)
{
    u32 h=0,n=0; s32 r,cr=0;
    r=openFile(smartMarkerPath,sizeof(smartMarkerPath),OPEN_READ|OPEN_WRITE|OPEN_CREATE,&h);
    if (!r) r=setSize(h,sizeof(*m),commandBuffer);
    if (!r) r=FILE_WRITE(&h,&n,0,m,sizeof(*m),WRITE_FLUSH);
    if (h) cr=FILE_CLOSE(&h);
    return !r && !cr && n==sizeof(*m);
}
static int smRead(SmartMarker *m)
{
    u32 h=0,n=0; u64 size=0; s32 r,cr=0;
    r=openFile(smartMarkerPath,sizeof(smartMarkerPath),OPEN_READ,&h);
    if (!r) r=FILE_GET_SIZE(&h,&size);
    if (!r && size==sizeof(*m)) r=FILE_READ(&h,&n,0,m,sizeof(*m));
    else if (!r) r=-1;
    if (h) cr=FILE_CLOSE(&h);
    return !r && !cr && n==sizeof(*m);
}
static unsigned smActiveProfile(void)
{
    u8 *registry=(u8 *)(*GAME_REGISTRY_SLOT),*model;
    if (!registry) return 0;
    model=(u8 *)GAME_MODEL_ACTIVE(*(void **)(registry+0x1C));
    return model?model[8]:0u;
}
static int smHeaderOk(const SmartMarker *m)
{
    const u8 *p=m->bytes;
    return p[0]=='O' && p[1]=='B' && p[2]=='R' && p[3]=='X' &&
        p[SM_OFF_VERSION]==SMART_MARKER_VERSION && p[SM_OFF_VERSION+1]==0u &&
        p[SM_OFF_PROFILE]>=1u && p[SM_OFF_PROFILE]<=8u &&
        smGet32(p+SM_OFF_CHECKSUM)==smChecksum(p);
}
static void smSeal(SmartMarker *m)
{
    smPut32(m->bytes+SM_OFF_CHECKSUM,smChecksum(m->bytes));
}
static void smZero(SmartMarker *m)
{
    unsigned i;
    for (i=0;i<sizeof(*m);i++) m->bytes[i]=0;
}

__attribute__((used,noinline,section(".text.official")))
void OfficialRecoverySmart_Clear(volatile u32 *commandBuffer)
{
    SmartMarker m;
    smZero(&m);
    (void)smWrite(&m,commandBuffer);
}

__attribute__((used,noinline,section(".text.official")))
void OfficialRecoverySmart_BulkApplied(volatile u32 *commandBuffer)
{
    SmartMarker m;
    unsigned profile=smActiveProfile();
    if (profile<1u || profile>8u) return;
    smZero(&m);
    m.bytes[0]='O'; m.bytes[1]='B'; m.bytes[2]='R'; m.bytes[3]='X';
    m.bytes[SM_OFF_VERSION]=SMART_MARKER_VERSION;
    m.bytes[SM_OFF_FLAGS]=(u8)SMART_FLAG_PENDING;
    m.bytes[SM_OFF_PROFILE]=(u8)profile;
    m.bytes[SM_OFF_STAGE]=SMART_STAGE_BULK_APPLIED;
    smSeal(&m);
    (void)smWrite(&m,commandBuffer);
}

__attribute__((used,noinline,section(".text.official")))
void OfficialRecoverySmart_GameSaveStarted(void *stateVoid,volatile u32 *commandBuffer)
{
    SmartMarker m;
    u8 *state=(u8 *)stateVoid,*p;
    u32 *tx;
    if (!state || !smRead(&m) || !smHeaderOk(&m)) return;
    p=m.bytes;
    if ((p[SM_OFF_FLAGS]&SMART_FLAG_PENDING)==0u || p[SM_OFF_STAGE]!=SMART_STAGE_BULK_APPLIED) return;
    tx=*(u32 **)(state+0x28);
    if (!tx) return;
    p[SM_OFF_FLAGS]=(u8)SMART_FLAG_BOUND;
    p[SM_OFF_STAGE]=SMART_STAGE_GAME_SAVE_STARTED;
    ((u32 *)(p+SM_OFF_DATA_ID))[0]=tx[0];
    ((u32 *)(p+SM_OFF_DATA_ID))[1]=tx[1];
    ((u32 *)(p+SM_OFF_PASSWORD))[0]=tx[6];
    ((u32 *)(p+SM_OFF_PASSWORD))[1]=tx[7];
    ((u32 *)(p+SM_OFF_CUR))[0]=tx[2];
    ((u32 *)(p+SM_OFF_UPDATE))[0]=tx[3];
    ((u32 *)(p+SM_OFF_SIZE))[0]=tx[4];
    smSeal(&m);
    (void)smWrite(&m,commandBuffer);
}

__attribute__((used,noinline,section(".text.official")))
void OfficialRecoverySmart_GameSaveOk(void *stateVoid,volatile u32 *commandBuffer)
{
    SmartMarker m;
    u8 *state=(u8 *)stateVoid,*p;
    u32 *tx;
    if (!state || !smRead(&m) || !smHeaderOk(&m)) return;
    p=m.bytes; tx=*(u32 **)(state+0x28);
    if (!tx || p[SM_OFF_STAGE]!=SMART_STAGE_GAME_SAVE_STARTED ||
        (p[SM_OFF_FLAGS]&SMART_FLAG_BOUND)==0u) return;
    if (((u32 *)(p+SM_OFF_DATA_ID))[0]!=tx[0] || ((u32 *)(p+SM_OFF_DATA_ID))[1]!=tx[1] ||
        ((u32 *)(p+SM_OFF_PASSWORD))[0]!=tx[6] || ((u32 *)(p+SM_OFF_PASSWORD))[1]!=tx[7] ||
        ((u32 *)(p+SM_OFF_CUR))[0]!=tx[2] || ((u32 *)(p+SM_OFF_UPDATE))[0]!=tx[3] ||
        ((u32 *)(p+SM_OFF_SIZE))[0]!=tx[4]) return;
    p[SM_OFF_STAGE]=SMART_STAGE_GAME_SAVE_OK;
    smSeal(&m);
    (void)smWrite(&m,commandBuffer);
}

__attribute__((used,noinline,section(".text.official")))
int OfficialRecoverySmart_Resolve(void *stateVoid)
{
    SmartMarker m;
    u8 *state=(u8 *)stateVoid,*p;
    u32 *tx,*dst;
    unsigned profile;
    if (!state || !smRead(&m) || !smHeaderOk(&m)) return 8;
    p=m.bytes; tx=*(u32 **)(state+0x28);
    profile=smActiveProfile();
    if (!tx || profile!=p[SM_OFF_PROFILE] || (p[SM_OFF_FLAGS]&SMART_FLAG_BOUND)==0u) return 8;
    if (((u32 *)(p+SM_OFF_DATA_ID))[0]!=tx[0] || ((u32 *)(p+SM_OFF_DATA_ID))[1]!=tx[1] ||
        ((u32 *)(p+SM_OFF_PASSWORD))[0]!=tx[6] || ((u32 *)(p+SM_OFF_PASSWORD))[1]!=tx[7] ||
        ((u32 *)(p+SM_OFF_CUR))[0]!=tx[2] || ((u32 *)(p+SM_OFF_UPDATE))[0]!=tx[3] ||
        ((u32 *)(p+SM_OFF_SIZE))[0]!=tx[4]) return 8;
    if (p[SM_OFF_STAGE]!=SMART_STAGE_GAME_SAVE_STARTED && p[SM_OFF_STAGE]!=SMART_STAGE_GAME_SAVE_OK) return 8;
    dst=(u32 *)(state+0x40);
    dst[0]=tx[0]; dst[1]=tx[1]; dst[2]=tx[2]; dst[3]=tx[3];
    dst[4]=tx[4]; dst[5]=tx[5]; dst[6]=tx[6]; dst[7]=tx[7];
    return p[SM_OFF_STAGE]==SMART_STAGE_GAME_SAVE_OK ? 5 : 6;
}
