#!/usr/bin/env python3
import argparse, hashlib, pathlib

BASE_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
CODE_BASE = 0x00100000
ALLOWED = [
    (0x002A8A74,0x002A8A78,"recovery invalid-status funnel"),
    (0x002A8AD0,0x002A8AD4,"recovery mismatch funnel"),
    (0x002A8B4C,0x002A8B6C,"recovery A rollback shim in unreachable case8 head"),
    (0x002AF460,0x002AF464,"BankDataSyncState_Update hook"),
    (0x00313910,0x00314000,"official RX text-tail payload"),
]
CAVES = [(0x00313910,0x00314000)]
EXPECTED_SYMBOLS = {
    "officialrecovery_a_rollbackshim":0x002A8B4C,
    "officialbulk_bankdatasyncdispatch":0x00313910,
    "officialbulksync_process":0x003139D4,
}
FORBIDDEN_SYMBOLS = {
    "officialbulk_commandbuffer",
}

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
    assert len(base)==len(patched), "patched .code size changed"
    for start,end in CAVES:
        assert not any(addr_slice(base,start,end)), f"base cave {start:08X}-{end:08X} is not zero"
    for i,(a,b) in enumerate(zip(base,patched)):
        if a==b: continue
        addr=CODE_BASE+i
        assert any(s<=addr<e for s,e,_ in ALLOWED), f"unexpected patched byte at {addr:08X}"
    assert addr_slice(base,0x002A8A74,0x002A8A78)!=addr_slice(patched,0x002A8A74,0x002A8A78)
    assert addr_slice(base,0x002A8AD0,0x002A8AD4)!=addr_slice(patched,0x002A8AD0,0x002A8AD4)
    assert addr_slice(base,0x002A8B4C,0x002A8B6C)!=addr_slice(patched,0x002A8B4C,0x002A8B6C)
    assert addr_slice(base,0x002AF460,0x002AF464)!=addr_slice(patched,0x002AF460,0x002AF464)
    assert addr_slice(base,0x0036A000,0x003AC000)==addr_slice(patched,0x0036A000,0x003AC000), \
        "official-only patch must not modify mapped data/BSS image"
    syms=read_symbols(args.symbols)
    for name,addr in EXPECTED_SYMBOLS.items():
        assert syms.get(name)==addr, f"symbol {name} expected {addr:08X}, got {syms.get(name)}"
    for name in FORBIDDEN_SYMBOLS:
        assert name not in syms, f"forbidden cross-ISA helper symbol present: {name}"
    replay=apply_ips(base,ips)
    assert replay==patched, "IPS replay does not reproduce patched .code"
    print("official bulk sync + recovery A static verification passed")

if __name__=="__main__": main()
