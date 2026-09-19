#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).with_name("main_official.s")
text = p.read_text(encoding="utf-8")

hook = ".org BankFlow_SelectNextState + 0x248"
assert hook in text, "missing post-download next-state patch"

pos = text.index(hook)
window = text[pos:pos + 240]
assert "moveq r0,#25" in window, "ordinary Bank download must jump directly to state 25"

# The feature is intentionally implemented at the outer transition.  Do not
# hook the reward state bodies themselves: that would alter their semantics for
# any unrelated path that may legitimately use them.
assert ".org RewardEligibilityState_Update" not in text
assert ".org RewardReceiveState_Update" not in text

print("skip-mileage source contract passed")
