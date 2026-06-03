# AUTO-ASSEMBLED decomposition bot (genotype hunter, gen 0).
# referee_policy=priority_order | specialists=['combat', 'space_control', 'food'] | tester=True | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'combat': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHRyeToKICAgICAgICBib2FyZCA9IGdhbWVfc3RhdGUuZ2V0KCJib2FyZCIsIHt9KQogICAgICAgIHlvdSA9IGdhbWVfc3RhdGUuZ2V0KCJ5b3UiLCB7fSkKICAgICAgICB3aWR0aCwgaGVpZ2h0ID0gYm9hcmQuZ2V0KCJ3aWR0aCIsIDExKSwgYm9hcmQuZ2V0KCJoZWlnaHQiLCAxMSkKICAgICAgICB5b3VyX2hlYWQgPSB5b3UuZ2V0KCJib2R5IiwgW3t9XSlbMF0KICAgICAgICB5b3VyX2xlbmd0aCA9IHlvdS5nZXQoImxlbmd0aCIsIDApCiAgICAgICAgeW91cl9ib2R5ID0geyhzWyJ4Il0sIHNbInkiXSkgZm9yIHMgaW4geW91LmdldCgiYm9keSIsIFtdKVsxOl19CgogICAgICAgIG1vdmVzID0geyJ1cCI6ICgwLCAxKSwgImRvd24iOiAoMCwgLTEpLCAibGVmdCI6ICgtMSwgMCksICJyaWdodCI6ICgxLCAwKX0KICAgICAgICBzY29yZXMgPSB7fQoKICAgICAgICAjIEJ1aWxkIG9jY3VwaWVkIHNldCBleGNsdWRpbmcgb3VyIHRhaWwgKHdlIGNhbiBtb3ZlIGludG8gaXQpCiAgICAgICAgb2NjdXBpZWQgPSBzZXQoKQogICAgICAgIGZvciBzbmFrZSBpbiBib2FyZC5nZXQoInNuYWtlcyIsIFtdKToKICAgICAgICAgICAgZm9yIHNlZ21lbnQgaW4gc25ha2UuZ2V0KCJib2R5IiwgW10pOgogICAgICAgICAgICAgICAgb2NjdXBpZWQuYWRkKChzZWdtZW50LmdldCgieCIsIDApLCBzZWdtZW50LmdldCgieSIsIDApKSkKICAgICAgICBvY2N1cGllZC5kaXNjYXJkKCh5b3UuZ2V0KCJib2R5IiwgW3t9XSlbLTFdLmdldCgieCIsIDApLCB5b3UuZ2V0KCJib2R5IiwgW3t9XSlbLTFdLmdldCgieSIsIDApKSkKCiAgICAgICAgZGVmIGhhc19lc2NhcGVfc3BhY2UocG9zLCBtaW5fc3BhY2U9NSk6CiAgICAgICAgICAgICIiIkJGUyB0byBjaGVjayBpZiBwb3NpdGlvbiBoYXMgZW5vdWdoIHJlYWNoYWJsZSBzcGFjZS4iIiIKICAgICAgICAgICAgaWYgcG9zIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAgICAgIHZpc2l0ZWQgPSB7cG9zfQogICAgICAgICAgICBxdWV1ZSA9IGRlcXVlKFtwb3NdKQogICAgICAgICAgICB3aGlsZSBxdWV1ZToKICAgICAgICAgICAgICAgIHgsIHkgPSBxdWV1ZS5wb3BsZWZ0KCkKICAgICAgICAgICAgICAgIGZvciBkeCwgZHkgaW4gWygwLCAxKSwgKDAsIC0xKSwgKDEsIDApLCAoLTEsIDApXToKICAgICAgICAgICAgICAgICAgICBueCwgbnkgPSB4ICsgZHgsIHkgKyBkeQogICAgICAgICAgICAgICAgICAgIGlmIDAgPD0gbnggPCB3aWR0aCBhbmQgMCA8PSBueSA8IGhlaWdodCBhbmQgKG54LCBueSkgbm90IGluIHZpc2l0ZWQgYW5kIChueCwgbnkpIG5vdCBpbiBvY2N1cGllZDoKICAgICAgICAgICAgICAgICAgICAgICAgdmlzaXRlZC5hZGQoKG54LCBueSkpCiAgICAgICAgICAgICAgICAgICAgICAgIHF1ZXVlLmFwcGVuZCgobngsIG55KSkKICAgICAgICAgICAgcmV0dXJuIGxlbih2aXNpdGVkKSA+PSBtaW5fc3BhY2UKCiAgICAgICAgZm9yIGRpcmVjdGlvbiwgKGR4LCBkeSkgaW4gbW92ZXMuaXRlbXMoKToKICAgICAgICAgICAgbnggPSB5b3VyX2hlYWQuZ2V0KCJ4IiwgMCkgKyBkeAogICAgICAgICAgICBueSA9IHlvdXJfaGVhZC5nZXQoInkiLCAwKSArIGR5CgogICAgICAgICAgICBpZiBueCA8IDAgb3IgbnggPj0gd2lkdGggb3IgbnkgPCAwIG9yIG55ID49IGhlaWdodDoKICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlmIChueCwgbnkpIGluIHlvdXJfYm9keToKICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIHRocmVhdCA9IEZhbHNlCiAgICAgICAgICAgIHdpbiA9IEZhbHNlCiAgICAgICAgICAgIGZvciBzbmFrZSBpbiBib2FyZC5nZXQoInNuYWtlcyIsIFtdKToKICAgICAgICAgICAgICAgIGlmIHNuYWtlLmdldCgiaWQiKSA9PSB5b3UuZ2V0KCJpZCIpOgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICBoZWFkID0gc25ha2UuZ2V0KCJib2R5IiwgW3t9XSlbMF0KICAgICAgICAgICAgICAgIGh4LCBoeSA9IGhlYWQuZ2V0KCJ4IiwgMCksIGhlYWQuZ2V0KCJ5IiwgMCkKICAgICAgICAgICAgICAgIGVuZW15X2xlbiA9IHNuYWtlLmdldCgibGVuZ3RoIiwgMCkKCiAgICAgICAgICAgICAgICBmb3IgZWR4LCBlZHkgaW4gWygwLCAxKSwgKDAsIC0xKSwgKC0xLCAwKSwgKDEsIDApXToKICAgICAgICAgICAgICAgICAgICBlbngsIGVueSA9IGh4ICsgZWR4LCBoeSArIGVkeQogICAgICAgICAgICAgICAgICAgIGlmIGVueCA9PSBueCBhbmQgZW55ID09IG55OgogICAgICAgICAgICAgICAgICAgICAgICBpZiBlbmVteV9sZW4gPj0geW91cl9sZW5ndGg6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aHJlYXQgPSBUcnVlCiAgICAgICAgICAgICAgICAgICAgICAgIGVsaWYgZW5lbXlfbGVuIDwgeW91cl9sZW5ndGg6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICB3aW4gPSBUcnVlCgogICAgICAgICAgICBpZiB0aHJlYXQ6CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgZWxpZiB3aW46CiAgICAgICAgICAgICAgICAjIE9ubHkgZW5jb3VyYWdlIHdpbiBpZiB3ZSBoYXZlIGVzY2FwZSBzcGFjZSBhZnRlciB0aGUgbW92ZQogICAgICAgICAgICAgICAgaWYgaGFzX2VzY2FwZV9zcGFjZSgobngsIG55KSwgbWluX3NwYWNlPTQpOgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gNS4wCiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gMC4wCiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IDAuMAoKICAgICAgICByZXR1cm4gc2NvcmVzCiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQo=', 'space_control': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHRyeToKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlWyJ5b3UiXQogICAgICAgIGJvYXJkID0gZ2FtZV9zdGF0ZVsiYm9hcmQiXQogICAgICAgIHdpZHRoLCBoZWlnaHQgPSBib2FyZFsid2lkdGgiXSwgYm9hcmRbImhlaWdodCJdCiAgICAgICAgeW91cl9sZW5ndGggPSB5b3VbImxlbmd0aCJdCiAgICAgICAgeW91cl9oZWFkID0gKHlvdVsiYm9keSJdWzBdWyJ4Il0sIHlvdVsiYm9keSJdWzBdWyJ5Il0pCiAgICAgICAgeW91cl9ib2R5ID0gWyhjZWxsWyJ4Il0sIGNlbGxbInkiXSkgZm9yIGNlbGwgaW4geW91WyJib2R5Il1dCiAgICAgICAgeW91cl90YWlsID0geW91cl9ib2R5Wy0xXQogICAgICAgIGp1c3RfYXRlID0gbGVuKHlvdVsiYm9keSJdKSA+IDEgYW5kIHlvdVsiYm9keSJdWy0xXVsieCJdID09IHlvdVsiYm9keSJdWy0yXVsieCJdIGFuZCB5b3VbImJvZHkiXVstMV1bInkiXSA9PSB5b3VbImJvZHkiXVstMl1bInkiXQoKICAgICAgICBvY2N1cGllZCA9IHNldCgpCiAgICAgICAgZm9yIHNuYWtlIGluIGJvYXJkWyJzbmFrZXMiXToKICAgICAgICAgICAgZm9yIGNlbGwgaW4gc25ha2VbImJvZHkiXToKICAgICAgICAgICAgICAgIG9jY3VwaWVkLmFkZCgoY2VsbFsieCJdLCBjZWxsWyJ5Il0pKQogICAgICAgIGlmIG5vdCBqdXN0X2F0ZToKICAgICAgICAgICAgb2NjdXBpZWQuZGlzY2FyZCh5b3VyX3RhaWwpCgogICAgICAgIGRlZiBmbG9vZF9maWxsKHN0YXJ0X3gsIHN0YXJ0X3kpOgogICAgICAgICAgICBpZiBzdGFydF94IDwgMCBvciBzdGFydF94ID49IHdpZHRoIG9yIHN0YXJ0X3kgPCAwIG9yIHN0YXJ0X3kgPj0gaGVpZ2h0OgogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgaWYgKHN0YXJ0X3gsIHN0YXJ0X3kpIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgdmlzaXRlZCA9IHsoc3RhcnRfeCwgc3RhcnRfeSl9CiAgICAgICAgICAgIHF1ZXVlID0gZGVxdWUoWyhzdGFydF94LCBzdGFydF95KV0pCiAgICAgICAgICAgIHdoaWxlIHF1ZXVlOgogICAgICAgICAgICAgICAgeCwgeSA9IHF1ZXVlLnBvcGxlZnQoKQogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0IGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZCBhbmQgKG54LCBueSkgbm90IGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgICAgICAgICB2aXNpdGVkLmFkZCgobngsIG55KSkKICAgICAgICAgICAgICAgICAgICAgICAgcXVldWUuYXBwZW5kKChueCwgbnkpKQogICAgICAgICAgICByZXR1cm4gbGVuKHZpc2l0ZWQpCgogICAgICAgIHJlc3VsdCA9IHt9CiAgICAgICAgYm9hcmRfYXJlYSA9IHdpZHRoICogaGVpZ2h0CiAgICAgICAgbWluX3NwYWNlX3RocmVzaG9sZCA9IG1heCh5b3VyX2xlbmd0aCAqIDAuOCwgNSkKCiAgICAgICAgZm9yIGRpcmVjdGlvbiwgKGR4LCBkeSkgaW4gWygidXAiLCAoMCwgMSkpLCAoImRvd24iLCAoMCwgLTEpKSwgKCJsZWZ0IiwgKC0xLCAwKSksICgicmlnaHQiLCAoMSwgMCkpXToKICAgICAgICAgICAgbmV3X3gsIG5ld195ID0geW91cl9oZWFkWzBdICsgZHgsIHlvdXJfaGVhZFsxXSArIGR5CiAgICAgICAgICAgIGlmIG5ld194IDwgMCBvciBuZXdfeCA+PSB3aWR0aCBvciBuZXdfeSA8IDAgb3IgbmV3X3kgPj0gaGVpZ2h0IG9yIChuZXdfeCwgbmV3X3kpIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgcmVzdWx0W2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICByZWFjaGFibGUgPSBmbG9vZF9maWxsKG5ld194LCBuZXdfeSkKICAgICAgICAgICAgICAgIGlmIHJlYWNoYWJsZSA8IG1pbl9zcGFjZV90aHJlc2hvbGQ6CiAgICAgICAgICAgICAgICAgICAgcmVzdWx0W2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIHJlc3VsdFtkaXJlY3Rpb25dID0gZmxvYXQocmVhY2hhYmxlKQogICAgICAgIHJldHVybiByZXN1bHQKICAgIGV4Y2VwdDoKICAgICAgICByZXR1cm4geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9Cg==', 'food': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKSAtPiBkaWN0OgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlWyJib2FyZCJdCiAgICAgICAgbXlfaGVhZCA9IHR1cGxlKHlvdVsiYm9keSJdWzBdLnZhbHVlcygpKSBpZiB5b3VbImJvZHkiXSBlbHNlIE5vbmUKICAgICAgICBteV9oZWFsdGggPSB5b3VbImhlYWx0aCJdCiAgICAgICAgbXlfbGVuZ3RoID0geW91WyJsZW5ndGgiXQogICAgICAgIGlmIG5vdCBteV9oZWFkOgogICAgICAgICAgICByZXR1cm4ge206IDAuMCBmb3IgbSBpbiBbInVwIiwgImRvd24iLCAibGVmdCIsICJyaWdodCJdfQogICAgICAgIHdpZHRoLCBoZWlnaHQgPSBib2FyZFsid2lkdGgiXSwgYm9hcmRbImhlaWdodCJdCgogICAgICAgIG9jY3VwaWVkID0gc2V0KCkKICAgICAgICBmb3Igc25ha2UgaW4gYm9hcmRbInNuYWtlcyJdOgogICAgICAgICAgICBmb3Igc2VnbWVudCBpbiBzbmFrZVsiYm9keSJdOgogICAgICAgICAgICAgICAgb2NjdXBpZWQuYWRkKHR1cGxlKHNlZ21lbnQudmFsdWVzKCkpKQogICAgICAgIG9jY3VwaWVkLmRpc2NhcmQoKHlvdVsiYm9keSJdWy0xXVsieCJdLCB5b3VbImJvZHkiXVstMV1bInkiXSkpCgogICAgICAgIGZvb2Rfc2V0ID0ge3R1cGxlKGYudmFsdWVzKCkpIGZvciBmIGluIGJvYXJkWyJmb29kIl19CiAgICAgICAgbG9uZ2VzdF9lbmVteSA9IG1heCgobGVuKHNbImJvZHkiXSkgZm9yIHMgaW4gYm9hcmRbInNuYWtlcyJdIGlmIHNbImlkIl0gIT0geW91WyJpZCJdKSwgZGVmYXVsdD0wKQogICAgICAgIHNob3VsZF9zZWVrX2Zvb2QgPSBteV9oZWFsdGggPCA0MCBvciBteV9sZW5ndGggPD0gbG9uZ2VzdF9lbmVteQoKICAgICAgICBkZWYgaXNfZGVhZF9lbmQoZm9vZF9wb3MpOgogICAgICAgICAgICB2aXNpdGVkID0ge2Zvb2RfcG9zfQogICAgICAgICAgICBxdWV1ZSA9IGRlcXVlKFtmb29kX3Bvc10pCiAgICAgICAgICAgIGNvdW50ID0gMQogICAgICAgICAgICB3aGlsZSBxdWV1ZToKICAgICAgICAgICAgICAgIHgsIHkgPSBxdWV1ZS5wb3BsZWZ0KCkKICAgICAgICAgICAgICAgIGZvciBkeCwgZHkgaW4gWygwLCAxKSwgKDAsIC0xKSwgKC0xLCAwKSwgKDEsIDApXToKICAgICAgICAgICAgICAgICAgICBueCwgbnkgPSB4ICsgZHgsIHkgKyBkeQogICAgICAgICAgICAgICAgICAgIGlmIDAgPD0gbnggPCB3aWR0aCBhbmQgMCA8PSBueSA8IGhlaWdodCBhbmQgKG54LCBueSkgbm90IGluIG9jY3VwaWVkIGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZDoKICAgICAgICAgICAgICAgICAgICAgICAgdmlzaXRlZC5hZGQoKG54LCBueSkpCiAgICAgICAgICAgICAgICAgICAgICAgIHF1ZXVlLmFwcGVuZCgobngsIG55KSkKICAgICAgICAgICAgICAgICAgICAgICAgY291bnQgKz0gMQogICAgICAgICAgICByZXR1cm4gY291bnQgPCBteV9sZW5ndGgKCiAgICAgICAgbW92ZXMgPSB7InVwIjogKDAsIDEpLCAiZG93biI6ICgwLCAtMSksICJsZWZ0IjogKC0xLCAwKSwgInJpZ2h0IjogKDEsIDApfQogICAgICAgIHNjb3JlcyA9IHt9CiAgICAgICAgZm9yIG1vdmVfbmFtZSwgKGR4LCBkeSkgaW4gbW92ZXMuaXRlbXMoKToKICAgICAgICAgICAgbngsIG55ID0gbXlfaGVhZFswXSArIGR4LCBteV9oZWFkWzFdICsgZHkKICAgICAgICAgICAgaWYgbm90ICgwIDw9IG54IDwgd2lkdGggYW5kIDAgPD0gbnkgPCBoZWlnaHQpIG9yIChueCwgbnkpIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgc2NvcmVzW21vdmVfbmFtZV0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBuZXdfaGVhZCA9IChueCwgbnkpCgogICAgICAgICAgICBpZiBzaG91bGRfc2Vla19mb29kOgogICAgICAgICAgICAgICAgc2FmZV9mb29kID0gW2YgZm9yIGYgaW4gZm9vZF9zZXQgaWYgbm90IGlzX2RlYWRfZW5kKGYpXQogICAgICAgICAgICAgICAgaWYgc2FmZV9mb29kOgogICAgICAgICAgICAgICAgICAgIGRpc3RhbmNlcyA9IFsoYWJzKGZbMF0gLSBuZXdfaGVhZFswXSkgKyBhYnMoZlsxXSAtIG5ld19oZWFkWzFdKSwgZikgZm9yIGYgaW4gc2FmZV9mb29kXQogICAgICAgICAgICAgICAgICAgIG1pbl9kaXN0ID0gbWluKGRbMF0gZm9yIGQgaW4gZGlzdGFuY2VzKQogICAgICAgICAgICAgICAgICAgIGlmIChueCwgbnkpIGluIGZvb2Rfc2V0OgogICAgICAgICAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV9uYW1lXSA9IDguMAogICAgICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gbWF4KDAuMCwgMTAuMCAtIG1pbl9kaXN0KQogICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV9uYW1lXSA9IDAuMAogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgc2NvcmVzW21vdmVfbmFtZV0gPSAwLjAKICAgICAgICByZXR1cm4gc2NvcmVzCiAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgIHJldHVybiB7bTogMC4wIGZvciBtIGluIFsidXAiLCAiZG93biIsICJsZWZ0IiwgInJpZ2h0Il19Cg=='}
_PRIORITY = ['combat', 'space_control', 'food']
_POLICY = 'priority_order'
_MERGE_B64 = ''

_SPECIALISTS = {}
for _n, _b in _SPEC_B64.items():
    _ns = {}
    try:
        exec(base64.b64decode(_b).decode("utf-8"), _ns)
        _f = _ns.get("score")
        _SPECIALISTS[_n] = _f if callable(_f) else None
    except Exception:
        _SPECIALISTS[_n] = None

_MERGE = None
if _MERGE_B64:
    _mns = {}
    try:
        exec(base64.b64decode(_MERGE_B64).decode("utf-8"), _mns)
        _f = _mns.get("referee")
        _MERGE = _f if callable(_f) else None
    except Exception:
        _MERGE = None

_MOVES = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
_VETO = -5e8


def info() -> dict:
    return {"apiversion": "1", "author": "decomp", "color": "#22aa88", "head": "default", "tail": "default"}


def start(game_state: dict) -> None:
    pass


def end(game_state: dict) -> None:
    pass


def _legal_moves(game_state):
    b = game_state["board"]
    w, h = b["width"], b["height"]
    head = game_state["you"]["body"][0]
    hx, hy = head["x"], head["y"]
    out = []
    for mv, (dx, dy) in _MOVES.items():
        x, y = hx + dx, hy + dy
        if 0 <= x < w and 0 <= y < h:
            out.append(mv)
    return out or list(_MOVES.keys())


def _collect(game_state):
    scores = {}
    for name, fn in _SPECIALISTS.items():
        if fn is None:
            continue
        try:
            s = fn(game_state)
            if isinstance(s, dict):
                scores[name] = {m: float(s.get(m, 0.0)) for m in _MOVES}
        except Exception:
            pass
    return scores


def _weighted_vote(scores, legal):
    best, bv = None, None
    for mv in legal:
        tot = 0.0
        for sc in scores.values():
            v = sc.get(mv, 0.0)
            tot += -1e6 if v <= _VETO else max(-50.0, min(50.0, v))
        if bv is None or tot > bv:
            bv, best = tot, mv
    return best or legal[0]


def _priority_order(scores, legal):
    vetoed = set()
    for sc in scores.values():
        for mv in legal:
            if sc.get(mv, 0.0) <= _VETO:
                vetoed.add(mv)
    pool = [m for m in legal if m not in vetoed] or list(legal)
    order = [n for n in _PRIORITY if n in scores]

    def key(mv):
        return tuple(-scores[n].get(mv, 0.0) for n in order)
    pool.sort(key=key)
    return pool[0]


def _occupied(game_state):
    occ = set()
    for s in game_state["board"]["snakes"]:
        body = [(c["x"], c["y"]) for c in s["body"]]
        ate = len(body) >= 2 and body[-1] == body[-2]
        for p in (body if ate else body[:-1]):  # tail vacates next turn unless it just ate
            occ.add(p)
    return occ


def _safe_moves(game_state, legal):
    """Legal moves that do NOT step into a snake body cell. The referee picks among these
    when any exist, so the bot never suicides into a body when a safe option is available
    (over-vetoing specialists must not be able to force a fatal move). Strategy still decides
    among the safe options."""
    occ = _occupied(game_state)
    head = game_state["you"]["body"][0]
    hx, hy = head["x"], head["y"]
    out = []
    for mv in legal:
        dx, dy = _MOVES[mv]
        if (hx + dx, hy + dy) not in occ:
            out.append(mv)
    return out


def move(game_state: dict) -> dict:
    try:
        legal = _legal_moves(game_state)
        safe = _safe_moves(game_state, legal)
        pool = safe if safe else legal
        scores = _collect(game_state)
        if not scores:
            choice = pool[0]
        elif _MERGE is not None:
            choice = _MERGE(scores, game_state, pool)
            if choice not in pool:
                choice = _weighted_vote(scores, pool)
        elif _POLICY == "priority_order":
            choice = _priority_order(scores, pool)
        else:
            choice = _weighted_vote(scores, pool)
        if choice not in _MOVES:
            choice = pool[0]
        return {"move": choice}
    except Exception:
        return {"move": "up"}
