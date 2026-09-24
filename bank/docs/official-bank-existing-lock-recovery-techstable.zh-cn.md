# PokÃ©mon Bank Recovery Cï¼šTechStable æŠ€æœ¯ç¨³å®šçŠ¶æ€

æ—¥æœŸï¼š2026-09-24  
åˆ†æ”¯ï¼š`feature/official-bank-existing-lock-recovery`  
ç”Ÿäº§ä»£ç åŸºçº¿ï¼š`d269d20a31d26993a28767aa0dba4aaca563dd97`

## çŠ¶æ€å®šä¹‰

Recovery C å½“å‰æ ‡è®°ä¸º **TechStable**ï¼š

- è®¾è®¡å·²æ”¶æ•›ä¸º Rollback-onlyï¼›
- ä¸ä¾èµ– Recovery A / Bï¼›
- ä¸ä½¿ç”¨ WALï¼›
- åª Hook state18 çš„ä¸¤æ¡çœŸå® game mismatch edgeï¼›
- ä¸ Hook å…¬å…± invalid-status / error funnelï¼›
- å¤ç”¨ stock state17 å®Œæˆå”¯ä¸€ä¸€æ¬¡è¿œç«¯ Rollback ä¸ game recovery cleanupï¼›
- host regressionã€ARM production buildã€RX tail budgetã€Windows armips link smokeã€branch target decode å‡å·²é€šè¿‡ã€‚

TechStable ä¸ç­‰äºå·²ç»å®Œæˆæ‰€æœ‰å®æœºæ•…éšœæ³¨å…¥ã€‚çœŸå®å·²é” Trainer mismatch å­˜æ¡£çš„ç«¯åˆ°ç«¯æ¢å¤æµ‹è¯•ä¸ç½‘ç»œ fault injection ä»åˆ—ä¸ºä¸‹ä¸€é˜¶æ®µéªŒè¯é¡¹ç›®ã€‚

## ç”Ÿäº§ Hook

```text
0x002AF460  BankDataSyncState_Update -> OfficialBulk_BankDataSyncDispatch
0x002A89D0  game dataId mismatch     -> OfficialExistingLock_GameMismatch
0x002A89E0  game curVersion mismatch -> OfficialExistingLock_GameMismatch
```

ä¸¤æ¡ mismatch branch çš„æœ€ç»ˆ ARM target å‡å·²ç”± CI è§£ç éªŒè¯ä¸ºï¼š

```text
0x00313934 OfficialExistingLock_GameMismatch
```

## Recovery C è¿è¡Œæ—¶é“¾è·¯

```text
state18 æŸ¥è¯¢åˆ° CURRENT server pending transaction
        â†“
stock local recovery æ— æ³•æ¢å¤
        â†“
game dataId / curVersion mismatch
        â†“
Recovery C è¯»å– [state18+0x28] CURRENT server tx
        â†“
å¤åˆ¶ T1 åˆ° state18 canonical transaction context
        â†“
åœ¨å†…å­˜ä¸­é‡å»º GameRecoveryRecord
status = 1
        â†“
state18 å®Œæˆå¹¶ result=4
        â†“
stock state17
        â†“
stock RollbackBankObject(T1)
        â†“
stock æ¸… transactionPassword
        â†“
stock game save writer æŒä¹…åŒ– cleanup
```

## æ˜ç¡®ç¦æ­¢çš„è¡Œä¸º

Recovery C ä¸ä¼šï¼š

- Commit å†å² pending transactionï¼›
- æ ¹æ®æ—§ local/game record çŒœæµ‹ Commitï¼›
- ä¾èµ–å·¥å…·äº‹å…ˆå†™å…¥ markerï¼›
- ç›´æ¥ NOP Trainer mismatchï¼›
- ä¿®æ”¹ PokÃ©mon box æ­£æ–‡ï¼›
- åœ¨ state18 å…ˆ Rollbackã€å†å¸¦ç€ stale status=2 è¿›å…¥ state17ã€‚

æœ€åä¸€é¡¹æ˜¯æœ¬ç‰ˆæœ€å…³é”®çš„å®‰å…¨çº¦æŸï¼šè¿œç«¯ Rollback åªç”± stock state17 æ‰§è¡Œä¸€æ¬¡ã€‚

## ç©ºé—´

```text
Bulk payload       1577 bytes
ARM dispatcher       36 bytes
Recovery C shim     128 bytes
--------------------------------
Total              1741 / 1776 bytes
Remain               35 bytes
```

æ‰€æœ‰æ–°å¢å¯æ‰§è¡Œä»£ç ä»é™åˆ¶åœ¨ï¼š

```text
0x00313910 .. 0x00314000
```

ä¸ä½¿ç”¨ `.data/BSS` ä½œä¸ºä»£ç åŒºã€‚

## å‘å¸ƒäº§ç‰©

æ­£å¼ IPS è·¯å¾„ï¼š

```text
release/00040000000C9B00/code.ips
```

ä»…é€‚ç”¨äº stock PokÃ©mon Banûï&‚‚˜^•]HQˆÎPŒ‹˜ÛÙHÚ^™NˆPÌ”ÒKLMˆˆ‘ÑMÎM‘MĞÑMÑŒPÑMŒMĞ‘Ì‘MPŒÌQĞMÑNLPÌMÌ‘ÍP‘‚˜‚”™XÛİ™\HÈXÚİX›HÛÙKš\Ø;ï&‚‚˜^œÚ^™HˆNMˆ]\Â”ÒKLMˆˆÍMMP‘Q‘Œ‘‘PLÌĞLŒMÑ‘LÑ‘MLÍMÍÌP‘PÎMLPLÌÌLÑQ‚˜‚’TÈ9k£9¥m9a¦yaiy."y.*ˆX]HÛÚÈ™XÛÜ™9.#¹¥m9.*ˆ–Z[;ï#9fè9«i9.#y/&¹fè9..¹æë¹¨!ù§.¹fj9è y.+yæ¡9keú" º #9aî¹ã¬™\›ËX˜\Ù[[™HY™ˆ9¯#ùa¦xà ‚‚ˆÈÈ9mìº`&º/áúj£:+àB‚‹H™XÛİ™\HÈÜİ™YÜ™\ÜÚ[Û‚‹HİØÚÈ™XÛİ™\H[Ù[™YÜ™\ÜÚ[Û‚‹HÙ™šXÚX[[È™YÜ™\ÜÚ[Û‚‹Hİ]XÈ™\šYšY\ˆŞ[^‹HT“]’È›ÙXİ[ÛˆØš™XİZ[‹H[œ™\ÛÛ™YŞ[X›ÛØ]B‹H–Z[YÙ]Ø]B‹HÚ[™İÜÈ\›Z\È›ÙXİ[Ûˆ[šÈÛ[ÚÙB‹H[šÙYŞ[X›Û™\Ù[˜ÙB‹HT“Hœ˜[˜Ú\™Ù]XÛÙB‹HTÈ™XÛÜ™Ü™\^HİXİ\™HØ]B‹H\›İ™Y]Úİ\™˜XÙHØ]B‚ˆÈÈ9.ãyo¡yk§¹§.ºj£:+àB‚‹H9mìºe H˜Z[™\ˆZ\ÛX]Ú9æ¡9ç'ùk§ˆÑÈ9kf9¨hù h¹i#B‹H›Û˜XÚÈ9d#¹k£9aj:` 9aîˆÈ9a£z/æùaiH˜[šÂ‹H9«hùn.˜[šÈ9/çykf9fç¹od‚‹HİYÙHÈØ[YK\Ø]™HÈÛX[\9ïdyîç9¥«yà®H˜][[š™Xİ[Û‚‚ºi¥¹«(yk§¹§.¹­bú+åy.ãyn¥9/oùå*9cëù h¹i#yi!ù.ïxà ‚