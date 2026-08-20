/*
 * Combined Bank patch shared local-file layer.
 *
 * 合并 Bank 补丁的共享本地文件层。
 *
 * The offline implementation is intentionally included as one translation unit.
 * This keeps its FS helpers private while allowing the download path to reuse
 * the exact checked tmp/bin/bak transaction instead of carrying a second FS
 * implementation.
 *
 * 离线实现被有意包含为同一个翻译单元。这样其 FS 辅助函数仍保持私有，同时
 * 下载路径能复用同一套经过检查的 tmp/bin/bak 事务，无须携带第二份 FS 实现。
 */
#include "../2-offline_patch/offline_patch.c"

/*
 * The download callback invokes OfflinePatch_Stage followed by
 * OfflinePatch_Commit directly from its assembly trampoline. Keeping that
 * wrapper out of this object preserves the complete payload within the
 * original optional-reward-state function extent.
 *
 * 下载回调会从汇编跳板直接依次调用 OfflinePatch_Stage 与
 * OfflinePatch_Commit。将该包装逻辑留在对象外，可使完整载荷保持在原票据
 * 可选奖励状态函数的范围内。
 */
