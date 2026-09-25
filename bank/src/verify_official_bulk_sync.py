#!/usr/bin/env python3
import argparse, hashlib, pathlib

BASE_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
CODE_BASE = 0x00100000
TAIL_START = 0x00313910
TAIL_END = 0x00314000
STOCK_GAME_SAVE_START = 0x002B4AB4

ALLOWED = [
    (0x002AF460,0x002AF464,"BankDataSyncState_Update hook"),
    (0x002A89D0,0x002A89D4,"Recovery C dataId mismatch edge"),
    (0x002A89E0,0x002A89E4,"Recovery C curVersion mismatch edge"),
    (0x002A61C8,0x002A61D0,"Recovery C state17 transient marker init"),
    (0x002A9518,0x002A951C,"Recovery C state17 synthetic-status hook"),
    (0x002A95F0,0x002A9618,"Recovery C4 persist-first state17 case5 block"),
    (0x002A966C,0x002A9670,"Recovery C state17 success result"),
    (0x002A970C,0x002A9710,"Recovery C state17 message id"),
    (TAIL_START,TAIL_END,"official RX text-tail payload"),
]
CAVES = [(TAIL_START,TAIL_END)]
REQUIRED_CHANGED = [
    (0x002AF460,0x002AF464,"BankDataSyncState_Update"),
    (0x002A89D0,0x002A89D4,"Recovery C dataId mismatch"),
    (0x002A89E0,0x002A89E4,"Recovery C curVersion mismatch"),
    (0x002A61C8,0x002A61D0,"Recovery C state17 transient marker init"),
    (0x002A9518,0x002A951C,"Recovery C state17 synthetic-status hook"),
    (0x002A95F0,0x002A9618,"Recovery C4 persist-first case5 block"),
    (0x002A966C,0x002A9670,"Recovery C state17 success result"),
    (0x002A970C,0x002A9710,"Recovery C state17 message id"),
]
STOCK_HOOK_BYTES = {
    (0x002A89D0,0x002A89D4): bytes.fromhex("3e00001a"),
    (0x002A89E0,0x002A89E4): bytes.fromhex("3a00001a"),
    (0x002A61C8,0x002A61D0): bytes.fromhex("6010c0e56110c0e5"),
    (0x002A9518,0x002A951C): bytes.fromhex("1c00d0e5"),
    (0x002A95F0,0x002A9618): bytes.fromhex(
        "0010a0e3080080e20120a0e1060080e80110a0e3000094e5"
        "182090e50400a0e132ff2fe10600a0e3"
    ),
    (0x002A966C,0x002A9670): bytes.fromhex("0400a0e3"),
    (0x002A970C,0x002A9710): bytes.fromhex("0e10a0e3"),
}
EXPECTED_PATCHED_BYTES = {
    (0x002A61C8,0x002A61D0): bytes.fromhex("0117a0e3601080e5"),
    (0x002A95F0,0x002A9618): bytes.fromhex(
        "6220d4e5030052e30200000a0010a0e3081080e50c1080e5"
        "0110a0e30400a0e1272d00eb0600a0e3"
    ),
    (0x002A966C,0x002A9670): bytes.fromhex("6200d4e5"),
    (0x002A970C,0x002A9710): bytes.fromhex("0c10a0e3"),
}
PRESERVED_STOCK_BYTES = {
    (0x002A9718,0x002A971C): bytes.fromhex("c1d0feeb"),
    # state17 vtable +0x18. C4 replaces the virtual dispatch with a direct BL
    # only because this exact Bank v1.5 vtable proves the target is 0x2B4AB4.
    (0x003619A4,0x003619A8): bytes.fromhex("b44a2b00"),
    (0x002B4AB4,0x002B4AB8): bytes.fromhex("70402de9"),
}
EXPECTED_TAIL_SYMBOLS = {
    "officialbulk_bankdatasyncdispatch",
    "officialexistinglock_state17status",
    "officialexistinglock_gamemismatch",
    "officialbulksync_process",
}
FORBIDDEN_SYMBOLS = {
    "officialbulk_commandbuffer",
    "officialrecovery_walcase1",
    "officialrecovery_wallocalstatusb",
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


def arm_branch_target(va, word):
    imm=word & 0x00FFFFFF
    if imm & 0x00800000:
        imm-=0x01000000
    return (va + 8 + imm * 4) & 0xFFFFFFFF


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
    for start,end in CAVES:
        assert not any(addr_slice(base,start,end)), f"base cave {start:08X}-{end:08X} is not zero"
    for (start,end),expected in STOCK_HOOK_BYTES.items():
        assert addr_slice(base,start,end)==expected, f"unexpected stock hook bytes at {start:08X}"
    for (start,end),expected in PRESERVED_STOCK_BYTES.items():
        assert addr_slice(base,start,end)==expected, f"unexpected stock preserved bytes at {start:08X}"

    changed=0
    for i,(a,b) in enumerate(zip(base,patched)):
        if a==b: continue
        changed+=1
        addr=CODE_BASE+i
        assert any(s<=addr<e for s,e,_ in ALLOWED), f"unexpected patched byte at {addr:08X}"
    assert changed, "patch produced no changes"

    for start,end,name in REQUIRED_CHANGED:
        assert addr_slice(base,start,end)!=addr_slice(patched,start,end), f"required hook not changed: {name}"
    for (start,end),expected in EXPECTED_PATCHED_BYTES.items():
        assert addr_slice(patched,start,end)==expected, f"unexpected patched bytes at {start:08X}"
    for (start,end),expected in PRESERVED_STOCK_BYTES.items():
        assert addr_slice(patched,start,end)==expected, f"required stock bytes changed at {start:08X}"
    assert addr_slice(base,0x0036A000,0x003AC000)==addr_slice(patched,0x0036A000,0x003AC000), \
        "Recovery C must not modify mapped data/BSS image"

    syms=read_symbols(args.symbols)
    assert syms.get("officialbulk_bankdatasyncdispatch")==TAIL_START, "dispatcher moved from RX-tail start"
    for name in EXPECTED_TAIL_SYMBOLS:
        assert name in syms, f"missing symbol {name}"
        addr=syms[name] & ~1
        assert TAIL_START<=addr<TAIL_END, f"symbol {name} escaped RX tail: {syms[name]:08X}"
    for name in FORBIDDEN_SYMBOLS:
        assert name not in syms, f"forbidden Recovery C symbol present: {name}"

    state17_word=int.from_bytes(addr_slice(patched,0x002A9518,0x002A951C),"little")
    assert (state17_word & 0xFF000000)==0xEA000000, \
        f"expected ARM B at state17 status hook, got {state17_word:08X}"
    expected=syms["officialexistinglock_state17status"] & ~1
    actual=arm_branch_target(0x002A9518,state17_word)
    assert actual==expected, f"state17 status hook target {actual:08X} != helper {expected:08X}"

    save_bl=int.from_bytes(addr_slice(patched,0x002A9610,0x002A9614),"little")
    assert (save_bl & 0xFF000000)==0xEB000000, f"expected ARM BL at C4 save call, got {save_bl:08X}"
    assert arm_branch_target(0x002A9610,save_bl)==STOCK_GAME_SAVE_START, \
        f"C4 save call does not target stock writer 0x{STOCK_GAME_SAVE_START:08X}"

    replay=apply_ips(base,ips)
    assert replay==patched, "IPS replay does not reproduce patched .code"
    print(f"official bulk sync + Recovery C4 verification passed; changed_bytes={changed}")


if __name__=="__main__": main()
