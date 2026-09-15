typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long long u64;

enum {
    ARCHIVE_SDMC = 9,
    PATH_EMPTY = 1,
    PATH_ASCII = 3,
    FS_OPEN_READ = 1,
    FS_OPEN_WRITE = 2,
    FS_OPEN_CREATE = 4,
    FS_WRITE_FLUSH = 1,
    BANKDATA_SIZE = 0xBB518
};

#define FSUSER_HANDLE_SLOT ((volatile u32 *)0x00390100u)
#define FSUSER_OPEN_FILE_DIRECTLY ((FsOpenFileDirectly)0x0022D338u)
#define FSFILE_WRITE ((FsFileWrite)0x0016594Cu)
#define FSFILE_CLOSE ((FsFileClose)0x00165920u)

typedef s32 (*FsOpenFileDirectly)(
    volatile u32 *fsHandle,
    u32 *fileHandle,
    u32 transaction,
    u32 archiveId,
    u32 archivePathType,
    const void *archivePathData,
    u32 archivePathSize,
    u32 filePathType,
    const void *filePathData,
    u32 filePathSize,
    u32 openFlags,
    u32 attributes);

typedef s32 (*FsFileWrite)(
    u32 *fileHandle,
    u32 *bytesWritten,
    u64 offset,
    const void *buffer,
    u32 size,
    u32 flags);

typedef s32 (*FsFileClose)(u32 *fileHandle);

static volatile u32 *getThreadCommandBuffer(void)
{
    u32 threadLocalStorage;
    __asm__ volatile("mrc p15, 0, %0, c13, c0, 3" : "=r"(threadLocalStorage));
    return (volatile u32 *)(threadLocalStorage + 0x80u);
}

static s32 sendSyncRequest(u32 handle)
{
    register u32 result __asm__("r0") = handle;
    __asm__ volatile("svc 0x32" : "+r"(result) : : "r1", "r2", "r3", "r12", "memory", "cc");
    return (s32)result;
}

static s32 openSdmcArchive(u64 *archive)
{
    static const char emptyPath[1] = { 0 };
    volatile u32 *commandBuffer = getThreadCommandBuffer();
    s32 result;

    commandBuffer[0] = 0x080C00C2u;
    commandBuffer[1] = ARCHIVE_SDMC;
    commandBuffer[2] = PATH_EMPTY;
    commandBuffer[3] = sizeof(emptyPath);
    commandBuffer[4] = (sizeof(emptyPath) << 14) | 2u;
    commandBuffer[5] = (u32)emptyPath;
    result = sendSyncRequest(*FSUSER_HANDLE_SLOT);
    if (result != 0) {
        return result;
    }
    result = (s32)commandBuffer[1];
    if (result == 0) {
        *archive = (u64)commandBuffer[2] | ((u64)commandBuffer[3] << 32);
    }
    return result;
}

static void createDirectory(u64 archive, const char *path, u32 pathSize)
{
    volatile u32 *commandBuffer = getThreadCommandBuffer();

    commandBuffer[0] = 0x08090182u;
    commandBuffer[1] = 0;
    commandBuffer[2] = (u32)archive;
    commandBuffer[3] = (u32)(archive >> 32);
    commandBuffer[4] = PATH_ASCII;
    commandBuffer[5] = pathSize;
    commandBuffer[6] = 0;
    commandBuffer[7] = (pathSize << 14) | 2u;
    commandBuffer[8] = (u32)path;
    (void)sendSyncRequest(*FSUSER_HANDLE_SLOT);
}

static void closeArchive(u64 archive)
{
    volatile u32 *commandBuffer = getThreadCommandBuffer();

    commandBuffer[0] = 0x080E0080u;
    commandBuffer[1] = (u32)archive;
    commandBuffer[2] = (u32)(archive >> 32);
    (void)sendSyncRequest(*FSUSER_HANDLE_SLOT);
}

static s32 deleteFile(u64 archive, const char *path, u32 pathSize)
{
    volatile u32 *commandBuffer = getThreadCommandBuffer();
    s32 result;

    commandBuffer[0] = 0x08040142u;
    commandBuffer[1] = 0;
    commandBuffer[2] = (u32)archive;
    commandBuffer[3] = (u32)(archive >> 32);
    commandBuffer[4] = PATH_ASCII;
    commandBuffer[5] = pathSize;
    commandBuffer[6] = (pathSize << 14) | 2u;
    commandBuffer[7] = (u32)path;
    result = sendSyncRequest(*FSUSER_HANDLE_SLOT);
    return result != 0 ? result : (s32)commandBuffer[1];
}

static s32 renameFile(u64 archive, const char *source, u32 sourceSize,
    const char *destination, u32 destinationSize)
{
    volatile u32 *commandBuffer = getThreadCommandBuffer();
    s32 result;

    commandBuffer[0] = 0x08050244u;
    commandBuffer[1] = 0;
    commandBuffer[2] = (u32)archive;
    commandBuffer[3] = (u32)(archive >> 32);
    commandBuffer[4] = PATH_ASCII;
    commandBuffer[5] = sourceSize;
    commandBuffer[6] = (u32)archive;
    commandBuffer[7] = (u32)(archive >> 32);
    commandBuffer[8] = PATH_ASCII;
    commandBuffer[9] = destinationSize;
    commandBuffer[10] = (sourceSize << 14) | 0x402u;
    commandBuffer[11] = (u32)source;
    commandBuffer[12] = (destinationSize << 14) | 0x802u;
    commandBuffer[13] = (u32)destination;
    result = sendSyncRequest(*FSUSER_HANDLE_SLOT);
    return result != 0 ? result : (s32)commandBuffer[1];
}

static void ensureCaptureDirectory(void)
{
    static const char directory3ds[] = "/3ds";
    static const char directoryBank[] = "/3ds/Bank";
    u64 archive = 0;

    if (openSdmcArchive(&archive) != 0) {
        return;
    }
    createDirectory(archive, directory3ds, sizeof(directory3ds));
    createDirectory(archive, directoryBank, sizeof(directoryBank));
    closeArchive(archive);
}

static s32 setFileSize(u32 fileHandle, u64 size)
{
    volatile u32 *commandBuffer = getThreadCommandBuffer();
    s32 result;

    commandBuffer[0] = 0x08050080u;
    commandBuffer[1] = (u32)size;
    commandBuffer[2] = (u32)(size >> 32);
    result = sendSyncRequest(fileHandle);
    if (result != 0) {
        return result;
    }
    return (s32)commandBuffer[1];
}

__attribute__((used, noinline, section(".text.download_patch")))
int DownloadPatch_SaveBankData(const void *bankData)
{
    static const char emptyPath[1] = { 0 };
    static const char bankDataPath[] = "/3ds/Bank/bankdata.bin";
    static const char bankDataTempPath[] = "/3ds/Bank/bankdata.tmp";
    static const char bankDataBackupPath[] = "/3ds/Bank/bankdata.bak";
    u64 archive = 0;
    u32 fileHandle = 0;
    u32 bytesWritten = 0;
    s32 openResult;
    s32 writeResult;

    if (bankData == (const void *)0) {
        return 0;
    }

    ensureCaptureDirectory();

    openResult = FSUSER_OPEN_FILE_DIRECTLY(
        FSUSER_HANDLE_SLOT,
        &fileHandle,
        0,
        ARCHIVE_SDMC,
        PATH_EMPTY,
        emptyPath,
        sizeof(emptyPath),
        PATH_ASCII,
        bankDataTempPath,
        sizeof(bankDataTempPath),
        FS_OPEN_READ | FS_OPEN_WRITE | FS_OPEN_CREATE,
        0);

    if (openResult != 0) {
        return 0;
    }

    if (setFileSize(fileHandle, BANKDATA_SIZE) != 0) {
        (void)FSFILE_CLOSE(&fileHandle);
        return 0;
    }

    writeResult = FSFILE_WRITE(
        &fileHandle,
        &bytesWritten,
        0,
        bankData,
        BANKDATA_SIZE,
        FS_WRITE_FLUSH);

    if (writeResult != 0 || bytesWritten != BANKDATA_SIZE) {
        (void)setFileSize(fileHandle, 0);
        (void)FSFILE_CLOSE(&fileHandle);
        return 0;
    }

    if (FSFILE_CLOSE(&fileHandle) != 0 || openSdmcArchive(&archive) != 0) {
        return 0;
    }

    (void)deleteFile(archive, bankDataBackupPath, sizeof(bankDataBackupPath));
    (void)renameFile(archive, bankDataPath, sizeof(bankDataPath),
        bankDataBackupPath, sizeof(bankDataBackupPath));
    writeResult = renameFile(archive, bankDataTempPath, sizeof(bankDataTempPath),
        bankDataPath, sizeof(bankDataPath));
    if (writeResult != 0) {
        (void)renameFile(archive, bankDataBackupPath, sizeof(bankDataBackupPath),
            bankDataPath, sizeof(bankDataPath));
    }
    closeArchive(archive);
    return writeResult == 0;
}
