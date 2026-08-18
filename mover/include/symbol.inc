; Poke Mover 00040000000C9C00 v5.5.0
; Curated symbols for patch development. Runtime addresses use image base 0x00100000.

; -----------------------------------------------------------------------------
; ExHeader memory layout
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
.definelabel TransferSlot_Load,                 0x0019A224
.definelabel TransferSlot_Write,                0x0019A6F4
.definelabel TransferSlot_Clear,                0x0019A7E0
.definelabel TransferSlot_IsOccupied,           0x0019A858
.definelabel TransferSlot_CountOccupied,        0x0024D624

; -----------------------------------------------------------------------------
; Main business states and offline patch boundaries
; -----------------------------------------------------------------------------
.definelabel MoverFlow_CreateStateObject,       0x0019CEE4
.definelabel MoverFlow_SelectNextState,         0x00242BA0
.definelabel MoverTransferEligibilityState_Update, 0x00248C68
.definelabel MoverTransferCommitState_Update,      0x0024A0C4
.definelabel MoverDownload_ConsumeBankData,        0x0025C978

.definelabel MoverPatch_SkipConnect,             0x00242D10
.definelabel MoverPatch_EnterEligibilityCheck,   0x00242D28
.definelabel MoverPatch_SkipEligibilityRequest,  0x00248CDC
.definelabel MoverPatch_EligibilityComplete,     0x00248D58
.definelabel MoverPatch_SkipGen5RemoteCheck,      0x00245728
.definelabel MoverPatch_SkipGen12RemoteCheck,     0x002460B8
.definelabel MoverPatch_Gen5InitSuccess,          0x002488A0
.definelabel MoverPatch_Gen12InitSuccess,         0x002483CC
.definelabel MoverPatch_SkipRemoteStage,          0x0024A150
.definelabel MoverPatch_CommitLocalFile,          0x0024A3D8

; Full-file staging, commit, and rollback call sites inside 0x0024A0C4.
.definelabel MoverSave_StageCall,                0x0024A240
.definelabel MoverSave_CommitCall,               0x0024A3E4
.definelabel MoverSave_RollbackCall,             0x0024A420

; -----------------------------------------------------------------------------
; HTTP, multipart, and HPP jobs
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
; Official interface definitions:
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
.definelabel FS_ArchiveId_SDMC,                  9
.definelabel FS_PathType_Empty,                  1
.definelabel FS_PathType_ASCII,                  3
.definelabel FSUSER_Cmd_OpenArchive,             0x080C00C2
.definelabel FSUSER_Cmd_CreateDirectory,         0x08090182
.definelabel FSUSER_Cmd_CloseArchive,            0x080E0080
.definelabel FSFILE_Cmd_SetSize,                 0x08050080
.definelabel SVC_SendSyncRequest,                0x32
