#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "official_bulk_sync.h"

static unsigned char *image(void)
{
    unsigned char *p=(unsigned char *)calloc(1,BANK_V15_SIZE);
    assert(p);
    p[BANK_V15_VERSION_OFFSET]=2;
    p[BANK_V15_BOX_COUNT_OFFSET]=100;
    return p;
}

static unsigned char *slot(unsigned char *p,unsigned box,unsigned s)
{
    return p+BANK_V15_MAIN_BOX_START+box*BANK_V15_BOX_STRIDE+s*BANK_V15_PKM_SIZE;
}

static unsigned index_of(unsigned box,unsigned s) { return box*30u+s; }

int main(void)
{
    unsigned char *runtime=image(),*bulk=image();
    unsigned char *homeRuntime=image(),*homeBulk=image();
    OfficialBulkMetadata meta={1u,32u,0x1122334455667788ULL};
    unsigned idx;
    char path[48];

    memset(slot(runtime,0,0),0x11,BANK_V15_PKM_SIZE);
    memset(slot(bulk,0,0),0x11,BANK_V15_PKM_SIZE);
    idx=index_of(0,0);
    runtime[BANK_V15_TAG_START+idx]=7;
    runtime[BANK_V15_SOURCE_START+idx]=9;
    *(uint64_t *)(runtime+BANK_V15_TIMESTAMP_START+idx*8u)=55;

    memset(slot(bulk,0,1),0x22,BANK_V15_PKM_SIZE);

    memset(slot(runtime,0,2),0x33,BANK_V15_PKM_SIZE);
    memset(slot(bulk,0,2),0x44,BANK_V15_PKM_SIZE);
    idx=index_of(0,2);
    runtime[BANK_V15_TAG_START+idx]=5;
    runtime[BANK_V15_SOURCE_START+idx]=6;
    *(uint64_t *)(runtime+BANK_V15_TIMESTAMP_START+idx*8u)=77;

    memset(slot(runtime,0,3),0x55,BANK_V15_PKM_SIZE);
    idx=index_of(0,3);
    runtime[BANK_V15_TAG_START+idx]=3;
    runtime[BANK_V15_SOURCE_START+idx]=4;
    *(uint64_t *)(runtime+BANK_V15_TIMESTAMP_START+idx*8u)=99;

    memset(runtime+BANK_V15_MAIN_BOX_START+BANK_V15_BOX_PKM_BYTES,0x66,BANK_V15_BOX_META_SIZE);
    memset(bulk+BANK_V15_MAIN_BOX_START+BANK_V15_BOX_PKM_BYTES,0x77,BANK_V15_BOX_META_SIZE);

    assert(OfficialBulk_ApplyDataOnly(runtime,bulk,BANK_G7_PKHEX_VIEW_SIZE,&meta)==1);

    idx=index_of(0,0);
    assert(runtime[BANK_V15_TAG_START+idx]==7);
    assert(runtime[BANK_V15_SOURCE_START+idx]==9);
    assert(*(uint64_t *)(runtime+BANK_V15_TIMESTAMP_START+idx*8u)==55);

    idx=index_of(0,1);
    assert(slot(runtime,0,1)[0]==0x22);
    assert(runtime[BANK_V15_TAG_START+idx]==1);
    assert(runtime[BANK_V15_SOURCE_START+idx]==32);
    assert(*(uint64_t *)(runtime+BANK_V15_TIMESTAMP_START+idx*8u)==meta.timestamp);

    idx=index_of(0,2);
    assert(slot(runtime,0,2)[0]==0x44);
    assert(runtime[BANK_V15_TAG_START+idx]==1);
    assert(runtime[BANK_V15_SOURCE_START+idx]==32);
    assert(*(uint64_t *)(runtime+BANK_V15_TIMESTAMP_START+idx*8u)==meta.timestamp);

    idx=index_of(0,3);
    for (unsigned i=0;i<BANK_V15_PKM_SIZE;i++) assert(slot(runtime,0,3)[i]==0);
    assert(runtime[BANK_V15_TAG_START+idx]==3);
    assert(runtime[BANK_V15_SOURCE_START+idx]==4);
    assert(*(uint64_t *)(runtime+BANK_V15_TIMESTAMP_START+idx*8u)==99);

    assert(!memcmp(runtime+BANK_V15_MAIN_BOX_START+BANK_V15_BOX_PKM_BYTES,
                   bulk+BANK_V15_MAIN_BOX_START+BANK_V15_BOX_PKM_BYTES,
                   BANK_V15_BOX_META_SIZE));

    memset(slot(homeRuntime,0,0),0x31,BANK_V15_PKM_SIZE);
    memset(slot(homeBulk,0,0),0x41,BANK_V15_PKM_SIZE);
    idx=index_of(0,0);
    homeRuntime[BANK_V15_TAG_START+idx]=0;
    homeRuntime[BANK_V15_SOURCE_START+idx]=17;
    *(uint64_t *)(homeRuntime+BANK_V15_TIMESTAMP_START+idx*8u)=0x8877665544332211ULL;
    memset(slot(homeBulk,0,1),0x51,BANK_V15_PKM_SIZE);
    assert(OfficialBulk_ApplyDataOnly(homeRuntime,homeBulk,BANK_G7_PKHEX_VIEW_SIZE,0)==1);
    idx=index_of(0,0);
    assert(slot(homeRuntime,0,0)[0]==0x41);
    assert(homeRuntime[BANK_V15_TAG_START+idx]==1);
    assert(homeRuntime[BANK_V15_SOURCE_START+idx]==17);
    assert(*(uint64_t *)(homeRuntime+BANK_V15_TIMESTAMP_START+idx*8u)==0x8877665544332211ULL);
    idx=index_of(0,1);
    assert(slot(homeRuntime,0,1)[0]==0x51);
    assert(homeRuntime[BANK_V15_TAG_START+idx]==1);
    assert(homeRuntime[BANK_V15_SOURCE_START+idx]==0);
    assert(*(uint64_t *)(homeRuntime+BANK_V15_TIMESTAMP_START+idx*8u)==0);

    runtime[0x160]=0xEA; runtime[0x161]=0x07; runtime[0x162]=9; runtime[0x163]=19;
    runtime[0x164]=11; runtime[0x165]=42; runtime[0x166]=7;
    assert(OfficialBulk_BuildBackupPath(runtime,path,sizeof(path))==1);
    assert(!strcmp(path,"/3ds/Bank/bankdata_20260919_114207.bin"));
    assert(OfficialBulk_FormatTagForProfile(1)==0);
    assert(OfficialBulk_FormatTagForProfile(4)==0);
    assert(OfficialBulk_FormatTagForProfile(5)==1);
    assert(OfficialBulk_FormatTagForProfile(8)==1);
    assert(OfficialBulk_FormatTagForProfile(0)==0xFF);
    assert(OfficialBulk_FormatTagForProfile(9)==0xFF);

    assert(OfficialBulk_ShouldProcessState(2u,1u,0u)==1);
    assert(OfficialBulk_ShouldProcessState(2u,1u,1u)==2);
    assert(OfficialBulk_ShouldProcessState(2u,0u,0u)==0);
    assert(OfficialBulk_ShouldProcessState(2u,0u,1u)==0);
    assert(OfficialBulk_ShouldProcessState(3u,1u,0u)==0);
    assert(OfficialBulk_ShouldProcessState(3u,1u,1u)==0);

    /* HOME state29: dirty=1 owns Stage/Commit; dirty=2 deliberately falls
       back to stock State29 rollback and only intercepts its completion. */
    assert(OfficialBulk_HomeCommitAction(0u,1u,0u,0u)==OFFICIAL_HOME_COMMIT_NATIVE);
    assert(OfficialBulk_HomeCommitAction(1u,1u,0u,0u)==OFFICIAL_HOME_COMMIT_START_STAGE);
    assert(OfficialBulk_HomeCommitAction(0x80u,1u,0u,0u)==OFFICIAL_HOME_COMMIT_WAIT);
    assert(OfficialBulk_HomeCommitAction(0x80u,1u,1u,0u)==OFFICIAL_HOME_COMMIT_START_COMMIT);
    assert(OfficialBulk_HomeCommitAction(0x80u,1u,1u,1u)==OFFICIAL_HOME_COMMIT_FALLBACK_ROLLBACK);
    assert(OfficialBulk_HomeCommitAction(0x81u,1u,0u,0u)==OFFICIAL_HOME_COMMIT_WAIT);
    assert(OfficialBulk_HomeCommitAction(0x81u,1u,1u,0u)==OFFICIAL_HOME_COMMIT_FINISH_SUCCESS);
    assert(OfficialBulk_HomeCommitAction(0x81u,1u,1u,1u)==OFFICIAL_HOME_COMMIT_FALLBACK_ROLLBACK);
    assert(OfficialBulk_HomeCommitAction(1u,2u,0u,0u)==OFFICIAL_HOME_COMMIT_NATIVE);
    assert(OfficialBulk_HomeCommitAction(2u,2u,0u,0u)==OFFICIAL_HOME_COMMIT_NATIVE);
    assert(OfficialBulk_HomeCommitAction(2u,2u,1u,0u)==OFFICIAL_HOME_COMMIT_FINISH_ERROR);
    assert(OfficialBulk_HomeCommitAction(2u,2u,1u,1u)==OFFICIAL_HOME_COMMIT_FINISH_ERROR);
    assert(OfficialBulk_HomeCommitAction(1u,0u,0u,0u)==OFFICIAL_HOME_COMMIT_NATIVE);

    free(runtime); free(bulk); free(homeRuntime); free(homeBulk);
    return 0;
}
