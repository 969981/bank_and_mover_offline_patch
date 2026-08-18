; Pokemon Bank 00040000000C9B00 v1.5
; Pokemon Bank 00040000000C9B00 软件内部版本 v1.5
; Curated symbols for patch development. Runtime addresses use image base 0x00100000.
; 用于补丁开发的精简符号。运行时地址使用镜像基址 0x00100000。

; -----------------------------------------------------------------------------
; ExHeader memory layout
; ExHeader 内存布局
; -----------------------------------------------------------------------------
.definelabel CodeImageBase,                     0x00100000
.definelabel TextActualEnd,                     0x00313910
.definelabel TextMappedEnd,                     0x00314000
.definelabel RodataMappedStart,                 0x00314000
.definelabel RodataMappedEnd,                   0x0036A000
.definelabel DataMappedStart,                   0x0036A000
.definelabel DataMappedEnd,                     0x003AC000

; -----------------------------------------------------------------------------
; Bank object and fixed-size serialized file
; Bank 对象和定长序列化文件
; -----------------------------------------------------------------------------
.definelabel BankFile_Size,                     0x000BB518
.definelabel BankFile_Vtable,                   0x003626FC
; Contains 0x003AB938.
; 内含 0x003AB938。
.definelabel BankRootPointerSlotAddressLiteral, 0x002ACEEC
.definelabel BankRootPointerSlot,               0x003AB938
.definelabel BankFile_InitializeEmpty,          0x00116294
.definelabel SizedObject_LoadBody,              0x0023650C
.definelabel CopyBytesOptimized,                0x0023653C
.definelabel BankFile_LoadLegacyBody,           0x002BA490
.definelabel BankFile_IsCurrentVersion,         0x002CB84C
.definelabel BankFile_GetSerializedSize,        0x002CB864
.definelabel BankFile_SerializeBody,            0x002CB870
.definelabel BankFile_DeriveFlowMetadata,       0x001D5EC0

; -----------------------------------------------------------------------------
; Main business states
; 主业务状态
; -----------------------------------------------------------------------------
.definelabel BankFlow_SelectNextState,          0x002A5580
.definelabel BankFlow_CreateStateObject,        0x002A5A7C
.definelabel BankMenuState_Update,              0x002A6750
.definelabel BankMenuState_SelectionCallback,   0x002A6C8C
.definelabel HomeTransferState_Update,           0x002A7BF0
.definelabel BankBoxUi_Update,                  0x002A7094
.definelabel DisconnectCleanupState_Update,      0x002ABC24
.definelabel ReturnToTitleState_Update,         0x002ABC24
.definelabel DisconnectCleanupState_Initialize, 0x002ABD38
.definelabel DisconnectCleanup_SkipRemoteJob,   0x002ABD94
.definelabel InitialRemoteRecordState_Update,   0x002ACBDC
.definelabel RewardEligibilityState_Update,     0x002AD1BC
.definelabel PostSelectionConnectionState_Update,0x002A93F4
.definelabel RewardReceiveState_Update,         0x002A9750
.definelabel BankCreateState_Update,            0x002AE568
.definelabel BankCreate_InitializeEmptyObject,   0x002AE8B0
.definelabel BankCreate_SuccessReturn,           0x002AE878
.definelabel BankNoSaveRollbackState_Update,     0x002AEB9C
.definelabel NetworkConnectionState_Initialize, 0x002AF34C
.definelabel NetworkConnectionState_Update,     0x002AF1FC
.definelabel NetworkConnection_AvailabilityCall,0x002AF37C
.definelabel NetworkConnection_SkipRemoteJob,    0x002AF38C
.definelabel NetworkConnection_StateTimerInitCall,0x002AF3D0
.definelabel BankFlow_PostSelectionMetadataPath, 0x002A58B4
.definelabel StateTimer_Reset,                  0x00229DB4
.definelabel StateTimer_HasElapsed,             0x001D5BB0
.definelabel BankDataSyncState_Update,          0x002AF460
.definelabel BankDataSyncState_Initialize,      0x002AFE38
.definelabel HomeRollbackState_Update,           0x002AFE94
.definelabel AccountTicketState_Update,          0x002B0270
.definelabel BankSaveState_Update,              0x002B1CF8
.definelabel BankSave_SerializeAndStage,        0x002B2320

; -----------------------------------------------------------------------------
; Remote BankObject transaction layer
; 远端 BankObject 事务层
; -----------------------------------------------------------------------------
.definelabel BankRemote_StageFileUpdate,        0x002A2504
.definelabel BankRemote_QueryMetadata,          0x002A26AC
.definelabel BankRemote_QueryRecoveryToken,     0x002A27C8
.definelabel BankRemote_UpdateMetadata,         0x002A2AD8
.definelabel BankRemote_CreateFile,             0x002A2E40
.definelabel BankRemote_RequestFile,            0x002A2F68
.definelabel BankRemote_QueryTransaction,       0x002A3144
.definelabel BankRemote_CreateSerializedFile,   0x002A37E0
.definelabel BankRemote_RollbackStagedUpdate,   0x001D5C28
.definelabel BankRemote_CommitStagedUpdate,     0x001D5D74
.definelabel BankRemote_QueryTransactionSuccessCallback, 0x002D0EDC
.definelabel BankRemote_DownloadSuccessCallback,         0x002D11B0

; -----------------------------------------------------------------------------
; HTTP, multipart, and HPP jobs
; HTTP、multipart 和 HPP 作业
; -----------------------------------------------------------------------------
.definelabel HttpRequest_PrepareAndStart,        0x00198A78
.definelabel HttpRequest_WorkerThread,           0x00199570
.definelabel MultipartFileStream_Build,          0x001C1EF8
.definelabel MultipartFileStream_ReadChunk,      0x001C22F0
.definelabel httpcSendPostDataRaw,               0x00245414
.definelabel httpcNotifyFinishSendPostData,      0x002454A4
.definelabel httpcReceiveData,                   0x002454C4
.definelabel HppPostJob_Init,                    0x001B23E8
.definelabel HppPostJob_ProcessResult,           0x001B2544
.definelabel HppPostJob_Retry,                   0x001B2820
.definelabel BankGetObject_PrepareRequest,       0x002CC878
.definelabel BankGetObject_CheckContentLength,  0x002CC988
.definelabel HppPostJob_PrepareRequest,          0x002CCE44
.definelabel HppPostJob_OnResponseBody,          0x002CCF28
.definelabel HppPostJob_OnResponseEvent,         0x002CD018
.definelabel HppPostJob_OnStatus,                0x002CD0B0

; -----------------------------------------------------------------------------
; FSUSER / FSFILE family
; FSUSER_OpenFileDirectly uses the application's 12-argument ARM ABI.
; FSFILE functions receive a pointer to the file handle used by this program.
; Official interface definitions:
; FSUSER / FSFILE 函数组。
; FSUSER_OpenFileDirectly 使用本程序的 12 参数 ARM ABI。
; FSFILE 函数接收本程序所用文件句柄的指针。
; 官方接口定义：
; https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/services/fs.h
; https://github.com/devkitPro/libctru/blob/master/libctru/source/services/fs.c
; -----------------------------------------------------------------------------
.definelabel FSUSER_HandleSlot,                  0x00390100
.definelabel FSUSER_OpenFileDirectly,            0x0022D338
.definelabel FSUSER_CreateFile,                  0x001654F8
.definelabel FSUSER_DeleteFile,                  0x00165554
.definelabel FSFILE_Read,                        0x001658C8
.definelabel FSFILE_Close,                       0x00165920
.definelabel FSFILE_Write,                       0x0016594C
.definelabel FSFILE_GetSize,                     0x001659AC
.definelabel MessageUi_Begin,                    0x001D5B44

; Raw IPC values used when no application wrapper is available.
; 在程序没有现成封装函数时使用的原始 IPC 值。
.definelabel FS_ArchiveId_SDMC,                  9
.definelabel FS_PathType_Empty,                  1
.definelabel FS_PathType_ASCII,                  3
.definelabel FSUSER_Cmd_OpenArchive,             0x080C00C2
.definelabel FSUSER_Cmd_DeleteFile,              0x08040142
.definelabel FSUSER_Cmd_RenameFile,              0x08050244
.definelabel FSUSER_Cmd_CreateDirectory,         0x08090182
.definelabel FSUSER_Cmd_CloseArchive,            0x080E0080
.definelabel FSFILE_Cmd_SetSize,                 0x08050080
.definelabel SVC_SendSyncRequest,                0x32
