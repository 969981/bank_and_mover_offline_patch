Pokemon Bank v1.5 - HOME Direct Bulk Sync PREVIEW
=================================================

分支:
  feature/home-direct-bulk-sync

源码提交:
  40ec6f18559312934c44342bca393a6e5a537f2c

GitHub Actions:
  run 35456214067
  compile-and-test: SUCCESS
  production Thumb object: 1680 bytes / 1680-byte budget

适用 Title ID:
  00040000000C9B00

安装:
  1. Luma3DS 启动配置中启用 Enable game patching。
  2. 将 code.ips 放到：
       SD:/luma/titles/00040000000C9B00/code.ips
  3. bulk_import.bin 放到：
       SD:/3ds/Bank/bulk_import.bin
  4. 启动 Pokemon Bank，选择 Pokemon HOME 路线进行测试。

当前 HOME-direct 流程:
  State 28: 官方下载 fresh BankObject -> fresh backup -> bulk merge
  State 29: StageFileUpdate(BankObject+8, 0xBB518) -> CompleteUpdate
            失败时回落原版 rollback
  State 27: 保持原版 HOME Moving Key / migration 流程

安全边界:
  - 不修改 State 27 / RequestMigration / Moving Key 协议。
  - HOME 路径不伪造 selected-game metadata。
  - bulk_import.bin 只读；不直接覆盖 header / identity / Transfer Box / remote state。
  - 自动备份仍写入 SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin。
  - Stage/Commit 失败不会继续进入 HOME migration。

首次实机验证建议:
  仅修改 1 个 Pokemon + 1 个 Box，确认 HOME 收到的数据正确后，再扩大到 30 -> 300 -> 3000。

发布等级:
  PREVIEW / EXPERIMENTAL
  CI 与静态二进制验证已通过；真实 Pokemon Bank -> HOME server round-trip 尚未标记为 stable。

哈希:
  Bank v1.5 base .code SHA-256:
    2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf
  code.ips SHA-256:
    6cbbe43a94fee35d1e5d52e500c7b93e4360e6227d1db704cb09475d77ca7503
  patched .code SHA-256:
    9c3b66ff66839abe422f5be4a8235f5bdba80f5a824b709330c4d3d6f4e18ea0
