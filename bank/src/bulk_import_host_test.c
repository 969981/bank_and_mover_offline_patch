#include "bulk_import.h"

static int expect(int condition)
{
    return condition?0:1;
}

int main(void)
{
    static unsigned char runtime[BANK_V15_SIZE];
    static unsigned char bulk[BANK_V15_SIZE];
    unsigned int i;
    int failures=0;

    for (i=0;i<BANK_V15_SIZE;i++) {
        runtime[i]=0x11;
        bulk[i]=0x22;
    }

    bulk[BANK_V15_VERSION_OFFSET]=2;
    bulk[BANK_V15_VERSION_OFFSET+1]=0;
    bulk[BANK_V15_BOX_COUNT_OFFSET]=100;
    bulk[BANK_V15_BOX_COUNT_OFFSET+1]=0;

    failures+=expect(BankBulk_ValidateHeader4(bulk+BANK_V15_VERSION_OFFSET));
    failures+=expect(BankBulk_IsSupportedInputSize(BANK_V15_SIZE));
    failures+=expect(BankBulk_IsSupportedInputSize(BANK_G7_PKHEX_VIEW_SIZE));
    failures+=expect(!BankBulk_IsSupportedInputSize(BANK_G7_PKHEX_VIEW_SIZE-1));
    BankBulk_ApplyMainBoxes(runtime,bulk);

    failures+=expect(runtime[0x000000]==0x11);
    failures+=expect(runtime[BANK_V15_MAIN_BOX_START-1]==0x11);
    failures+=expect(runtime[BANK_V15_MAIN_BOX_START]==0x22);
    failures+=expect(runtime[BANK_V15_MAIN_BOX_END-1]==0x22);
    failures+=expect(runtime[BANK_V15_MAIN_BOX_END]==0x11);
    failures+=expect(runtime[0x0ACA44]==0x11);
    failures+=expect(runtime[BANK_V15_SIZE-1]==0x11);

    return failures;
}
