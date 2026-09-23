#!/usr/bin/env python3
import argparse, hashlib, pathlib

BASE_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
CODE_BASE = 0x00100000
TAIL_START = 0x00313910
TAIL_END = 0x00314000

# Variant A is deliberately minimal: Bulk entry + pre-RMC52 case1 diversion +
# case8 journal-result hook. case7 stays native status=1 and state18 is stock.
ALLOWED = [
    (0x002AF460,0x002AF464,"BankDataSyncState_Update hook"),
    (0x002B1DE4,0x002B1DE8,"recovery A pre-RMC52 journal entry"),
    (0x002B2090,0x002B2094,"recovery A case8 journal result"),
    (TAIL_START,TAIL_END,"official RX text-tail payload"),
]
REQUIRED_CHANGED = [
    (0x002AF460,0x002AF464,"BankDataSyncState_Update"),
    (0x002B1DE4,0x002B1DE8,"A case1 prejournal"),
    (0x002B2090,0x002B2094,"A case8 result"),
]
# These are intentionally stock in A and guard against accidentally drifting
# back toward the older private-status/state18-hook implementation.
REQUIRED_STOCK = [
    (0x002B1FFC,0x002B2000,"stock case7 status=1"),
    (0x002A8968,0x002A897C,"stock local recovery status decision"),
    (0x002A89D0,0x002A89D4,"stock game dataId mismatch branch"),
    (0x002A89E0,0x002A89E4,"stock game curVersion mismatch branch"),
]
EXPECTED_TAIL_SYMBOLS = {
    "officialbulk_bankdatasyncdispatch",
    "officialrecovery_walcase1",
    "officialrecovery_walcase8result",
    "officialbulksync_process",
}
FORBIDDEN_SYMBOLS = {"officialbulk_commandbuffer"}


def addr_slice(data,start,end):
    return data[start-CODE_BASE:end-CODE_BASE]


def read_symbols(path):
    out={}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        parts=line.split()
        if len(parts)>=2:
            try: out[parts[1].lower()]=int(parts[0],16)
            except ValueError: pass
    return out


def apply_ips(base,patch):
    if not patch.startswith(b"PATCH") or not patch.endswith(b"EOF"):
        raise AssertionError("invalid IPS header/footer")
    out=bytearray(base); p=5
    while patch[p:p+3]!=b"EOF":
        off=int.from_bytes(patch[p:p+3],"big"); p+=3
        size=int.from_bytes(patch[p:p+2],"big"); p+=2
        if size:
            data=patch[p:p+size]; p+=size
        else:
            rle=int.from_bytes(patch[p:p+2],"big"); p+=2
            value=patch[p]; p+=1
            data=bytes([value])*rle
        end=off+len(data)
        if end>len(out): out.extend(b"\0"*(end-len(out)))
        out[off:end]=data
    return bytes(out)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True); ap.add_argument("--patched",required=True)
    ap.add_argument("--symbols",required=True); ap.add_argument("--ips",required=True)
    args=ap.parse_args()
    base=pathlib.Path(args.base).read_bytes(); patched=pathlib.Path(args.patched).read_bytes()
    ips=pathlib.Path(args.ips).read_bytes()
    assert hashlib.sha256(base).hexdigest()==BASE_SHA256, "unexpected Bank v1.5 base SHA-256"
    assert len(base)==len(patched)==0x2AC000, "patched .code size changed"
    assert not any(addr_slice(base,TAIL_START,TAIL_END)), "verified RX tail is not zero in stock image"

    changed=0
    for i,(a,b) in enumerate(zip(base,patched)):
        if a==b: continue
        changed+=1
        addr=CODE_BASE+i
        assert any(s<=addr<e for s,e,_ in ALLOWED), f"unexpected patched byte at {addr:08X}"
    assert changed, "patch produced no changes"

    for start,end,name in REQUIRED_CHANGED:
        assert addr_slice(base,start,end)!=addr_slice(patched,start,end), f"required hook not changed: {name}"
    for start,end,name in REQUIRED_STOCK:
        assert addr_slice(base,start,end)==addr_slice(patched,start,end), f"A must preserve {name}"
    assert addr_slice(base,0x0036A000,0x003AC000)==addr_slice(patched,0x0036A000,0x003AC000), \
        "official recovery patch must not modify mapped data/BSS image"

    syms=read_symbols(args.symbols)
    assert syms.get("officialbulk_bankdatasyncdispatch")==TAIL_START, "dispatcher moved from RX-tail start"
    for name in EXPECTED_TAIL_SYMBOLS:
        assert name in syms, f"missing symbol {name}"
        addr=syms[name] & ~1
        assert TAIL_START<=addr<TAIL_END, f"symbol {name} escaped RX tail: {syms[name]:08X}"
    for name in FORBIDDEN_SYMBOLS:
        assert name not in syms, f"forbidden helper symbol present: {name}"

    replay=apply_ips(base,ips)
    assert replay==patched, "IPS replay does not reproduce patched .code"
    print(f"official bulk sync + recovery A verification passed; changed_bytes={changed}")


if __name__=="__main__": main()
