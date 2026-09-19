#!/usr/bin/env python3
import argparse, hashlib, pathlib

BASE_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
CODE_BASE = 0x00100000
ALLOWED = [
    (0x002AF460,0x002AF464,"BankDataSyncState_Update hook"),
    (0x002D11C4,0x002D11C8,"DownloadSuccess callback marker hook"),
    (0x00313910,0x00314008,"official runtime cave"),
    (0x003ABA90,0x003ABFFC,"official core cave"),
]
CAVES = [(0x00313910,0x00314008),(0x003ABA90,0x003ABFFC)]
EXPECTED_SYMBOLS = {
    "officialbulk_downloadmarkertrampoline":0x00313910,
    "officialbulk_bankdatasyncdispatch":0x00313958,
    "officialbulksync_process":0x0031398C,
    "officialbulk_corestart":0x003ABA90,
    "officialbulk_scratch":0x003ABFFC,
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
    assert addr_slice(base,0x002AF460,0x002AF464)!=addr_slice(patched,0x002AF460,0x002AF464)
    assert addr_slice(base,0x002D11C4,0x002D11C8)!=addr_slice(patched,0x002D11C4,0x002D11C8)
    assert addr_slice(patched,0x003ABFFC,0x003AC000)==addr_slice(base,0x003ABFFC,0x003AC000), "scratch must stay zero in file"
    syms=read_symbols(args.symbols)
    for name,addr in EXPECTED_SYMBOLS.items():
        assert syms.get(name)==addr, f"symbol {name} expected {addr:08X}, got {syms.get(name)}"
    replay=apply_ips(base,ips)
    assert replay==patched, "IPS replay does not reproduce patched .code"
    print("official bulk sync static verification passed")

if __name__=="__main__": main()
