; Poke Mover 00040000000C9C00 v5.5.0
; Poke Mover 00040000000C9C00 软件内部版本 v5.5.0
; Curated symbols for patch development. Runtime addresses use image base 0x00100000.
; 用于补丁开发的精简符号。运行时地址使用镜像基址 0x00100000。

; -----------------------------------------------------------------------------
; ExHeader memory layout
; ExHeader 内存布局
; -----------------------------------------------------------------------------
.definelabel CodeImageBase,                     0x00100000
.definelabel TextActualEnd,                     0x0028D1AC
.definelabel TextMappedEnd,                     0x0028E000
.definelabel RodataMappedStart,                 0x0028E000
.definelabel RodataMappedEnd,                   0x002EC000
.definelabel DataMappedStart,                   0x002EC000
.definelabel DataMappedEnd,                     0x0032A000

; -----------------------------------------------------------------------------
; Bank object and fixed-size serialized file
; Bank 对象和定长序列化文件
; -----------------------------------------------------------------------------
.definelabel BankFile_Size,                     0x000BB518
.definelabel BankFile_Vtable,                   0x002E6DD0
.definelabel TransferBox_DataOffset,            0x000AAF14
.definelabel TransferBox_TagOffset,             0x000AD5FC
.definelabel TransferBox_SlotSize,              0x000000E8
.definelabel TransferBox_SlotCount,             30
.definelabel BankFile_LoadBody,                 0x0024D868
.definelabel BankFile_LoadLegacyBody,           0x0024D898
.definelabel BankFile_IsCurrentVersion,         0x0025AE20
.definelabel BankFile_GetSerializedSize,        0x0025AE38
.definelabel BankFile_SerializeBody,            0x0025AE44

; Transfer Box operations update both the 0xE8-byte record and its tag.
; 传送盒操作会同时更新 0xE8 字节槽记录及其标签。
.definelabel Heap_AllocateObject,               0x001E6360
.definelabel TransferObject_Create,             0x001DFBA4
.definelabel TransferSlot_Load,                 0x0019A224
.definelabel TransferSlot_Write,                0x0019A6F4
.definelabel TransferSlot_Clear,                0x0019A7E0
.definelabel TransferSlot_IsOccupied,           0x0019A858
.definelabel TransferSlot_CountOccupied,        0x0024D624

; -----------------------------------------------------------------------------
; Main business states and offline patch boundaries
; 主业务状态与离线补丁边界
; -----------------------------------------------------------------------------
.definelabel MoverFlow_CreateStateObject,       0x0019CEE4
.definelabel MoverFlow_SelectNextState,         0x00242BA0
.definelabel MoverDisconnectState_Update,       0x0024709C
.definelabel MoverDisconnectState_Initialize,   0x00247234
.definelabel MoverDisconnect_SkipRemoteJob,     0x00247290
.definelabel MoverNetworkState_Update,          0x00248A08
.definelabel MoverNetworkState_Initialize,      0x00248B58
.definelabel MoverNetwork_AvailabilityCall,     0x00248B88
.definelabel MoverNetwork_SkipRemoteJob,         0x00248B98
.definelabel MoverNetwork_StateTimerInitCall,    0x00248BDC
.definelabel StateTimer_Reset,                   0x00233844
.definelabel StateTimer_HasElapsed,              0x0019B758
.definelabel MoverTicketState_Update,           0x00249600
.definelabel MoverRemoteCheckState_Update,      0x00248814
.definelabel MoverTransferEligibilityState_Update, 0x00248C68
.definelabel MoverNoTransferState_Update,         0x00248360
.definelabel MoverTransferCommitState_Update,      0x0024A0C4
.definelabel MoverDownload_ConsumeBankData,        0x0025C978
.definelabel MoverGetPokemonState_Update,           0x002455D0

; Remote legality checks embedded in the native candidate-conversion state.
; 原版候选转换状态中嵌入的远端合法性检查。
.definelabel MoverGetPokemon_SkipGen5RemoteValidation, 0x00245728
.definelabel MoverGetPokemon_Gen5LocalContinuation,    0x00245800
.definelabel MoverGetPokemon_SkipGen12RemoteValidation,0x002460B8
.definelabel MoverGetPokemon_Gen12LocalContinuation,   0x002461D0

; State-transition and save patch sites used by the offline implementation.
; 离线实现所使用的状态转移和保存补丁位置。
.definelabel MoverFlow_RemoteCheckSuccessState,  0x00242D4C
.definelabel MoverSave_SkipRemoteJob,            0x0024A150

; Full-file staging, commit, and rollback call sites inside 0x0024A0C4.
; 0x0024A0C4 内完整文件的暂存、提交和回滚调用位置。
.definelabel MoverSave_StageCall,                0x0024A240
.definelabel MoverSave_AfterStageState,          0x0024A248
.definelabel MoverSave_StageWaitState,           0x0024A258
.definelabel MoverSave_UpdateEpilogue,            0x0024A5DC
.definelabel MoverSave_CommitCall,               0x0024A3E4
.definelabel MoverSave_AfterCommitState,         0x0024A3EC
.definelabel MoverSave_RollbackCall,             0x0024A420
.definelabel MoverSave_AfterRollbackState,       0x0024A428

; -----------------------------------------------------------------------------
; HTTP, multipart, and HPP jobs
; HTTP、multipart 和 HPP 作业
; -----------------------------------------------------------------------------
.definelabel HttpRequest_PrepareAndStart,        0x0018AA38
.definelabel HttpRequest_WorkerThread,           0x0018B58C
.definelabel MultipartFileStream_Build,          0x0020815C
.definelabel MultipartFileStream_ReadChunk,      0x00208554
.definelabel httpcSendPostDataRaw,               0x00215208
.definelabel httpcNotifyFinishSendPostData,      0x00215308
.definelabel httpcReceiveData,                   0x00215328
.definelabel HppPostJob_Init,                    0x001F8D5C
.definelabel HppPostJob_ProcessResult,           0x001F8EB8
.definelabel HppPostJob_Retry,                   0x001F9194
.definelabel BankGetObject_PrepareRequest,       0x0025AF1C
.definelabel BankGetObject_CheckContentLength,  0x0025B02C
.definelabel HppPostJob_PrepareRequest,          0x0025B76C
.definelabel HppPostJob_OnResponseBody,          0x0025B850
.definelabel HppPostJob_OnResponseEvent,         0x0025B940
.definelabel HppPostJob_OnStatus,                0x0025B9D8

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
.definelabel FSUSER_HandleSlot,                  0x00311F80
.definelabel FSUSER_OpenFileDirectly,            0x001DF448
.definelabel FSUSER_DeleteFile,                  0x00158FC8
.definelabel FSFILE_Read,                        0x0015930C
.definelabel FSFILE_Close,                       0x00159364
.definelabel FSFILE_Write,                       0x00159390
.definelabel FSFILE_GetSize,                     0x001593F0

; Raw IPC values used when no application wrapper is available.
; 在程序没有现成封装函数时使用的原始 IPC 值。
.definelabel FS_ArchiveId_SDMC,                  9
.definelabel FS_PathType_Empty,                  1
.definelabel FS_PathType_ASCII,                  3
.definelabel FSUSER_Cmd_OpenArchive,             0x080C00C2
.definelabel FSUSER_Cmd_CreateDirectory,         0x08090182
.definelabel FSUSER_Cmd_DeleteFile,              0x08040142
.definelabel FSUSER_Cmd_RenameFile,              0x08050244
.definelabel FSUSER_Cmd_CloseArchive,            0x080E0080
.definelabel FSFILE_Cmd_SetSize,                 0x08050080
.definelabel SVC_SendSyncRequest,                0x32
