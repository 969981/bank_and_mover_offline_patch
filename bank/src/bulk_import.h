#ifndef BANK_BULK_IMPORT_H
#define BANK_BULK_IMPORT_H

#define BANK_V15_SIZE 0xBB518u
#define BANK_V15_VERSION_OFFSET 0x15Cu
#define BANK_V15_BOX_COUNT_OFFSET 0x15Eu
#define BANK_V15_MAIN_BOX_START 0x17Cu
#define BANK_V15_MAIN_BOX_END 0xAAF14u
#define BANK_V15_MAIN_BOX_SIZE (BANK_V15_MAIN_BOX_END-BANK_V15_MAIN_BOX_START)

static int BankBulk_ValidateHeader4(const unsigned char header[4])
{
    unsigned int version=(unsigned int)header[0]|((unsigned int)header[1]<<8);
    unsigned int boxCount=(unsigned int)header[2]|((unsigned int)header[3]<<8);
    return version==2u && boxCount==100u;
}

static void BankBulk_ApplyMainBoxes(unsigned char *runtimeBody,
    const unsigned char *bulkBody)
{
    unsigned int offset;
    for (offset=BANK_V15_MAIN_BOX_START;offset<BANK_V15_MAIN_BOX_END;offset++)
        runtimeBody[offset]=bulkBody[offset];
}

#endif
