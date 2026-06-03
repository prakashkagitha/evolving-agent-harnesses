# AUTO-ASSEMBLED decomposition bot (genotype duelist, gen 0).
# referee_policy=weighted_vote | specialists=['combat', 'endgame', 'space_control'] | tester=True | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'combat': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlWyJib2FyZCJdCiAgICAgICAgbXlfaGVhZCA9IHR1cGxlKFt5b3VbImJvZHkiXVswXVsieCJdLCB5b3VbImJvZHkiXVswXVsieSJdXSkKICAgICAgICBteV9sZW5ndGggPSB5b3VbImxlbmd0aCJdCiAgICAgICAgbXlfYm9keV9zZXQgPSB7KHNlZ1sieCJdLCBzZWdbInkiXSkgZm9yIHNlZyBpbiB5b3VbImJvZHkiXX0KICAgICAgICBteV90YWlsID0gdHVwbGUoW3lvdVsiYm9keSJdWy0xXVsieCJdLCB5b3VbImJvZHkiXVstMV1bInkiXV0pCiAgICAgICAganVzdF9hdGUgPSBsZW4oeW91WyJib2R5Il0pID4gMSBhbmQgeW91WyJib2R5Il1bLTFdWyJ4Il0gPT0geW91WyJib2R5Il1bLTJdWyJ4Il0gYW5kIHlvdVsiYm9keSJdWy0xXVsieSJdID09IHlvdVsiYm9keSJdWy0yXVsieSJdCgogICAgICAgIHJlc3VsdCA9IHt9CiAgICAgICAgbW92ZXMgPSBbKCJ1cCIsIDAsIDEpLCAoImRvd24iLCAwLCAtMSksICgibGVmdCIsIC0xLCAwKSwgKCJyaWdodCIsIDEsIDApXQoKICAgICAgICBmb3IgZGlyZWN0aW9uLCBkeCwgZHkgaW4gbW92ZXM6CiAgICAgICAgICAgIG5leHRfeCwgbmV4dF95ID0gbXlfaGVhZFswXSArIGR4LCBteV9oZWFkWzFdICsgZHkKICAgICAgICAgICAgbmV4dF9oZWFkID0gKG5leHRfeCwgbmV4dF95KQoKICAgICAgICAgICAgaWYgbm90ICgwIDw9IG5leHRfeCA8IGJvYXJkWyJ3aWR0aCJdIGFuZCAwIDw9IG5leHRfeSA8IGJvYXJkWyJoZWlnaHQiXSk6CiAgICAgICAgICAgICAgICByZXN1bHRbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBpZiBuZXh0X2hlYWQgaW4gbXlfYm9keV9zZXQgYW5kIG5vdCAobm90IGp1c3RfYXRlIGFuZCBuZXh0X2hlYWQgPT0gbXlfdGFpbCk6CiAgICAgICAgICAgICAgICByZXN1bHRbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBzY29yZV92YWwgPSAwLjAKICAgICAgICAgICAgdmV0byA9IEZhbHNlCgogICAgICAgICAgICBmb3IgZW5lbXkgaW4gYm9hcmRbInNuYWtlcyJdOgogICAgICAgICAgICAgICAgaWYgZW5lbXlbImlkIl0gPT0geW91WyJpZCJdOgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICAgICAgZW5lbXlfaGVhZCA9IHR1cGxlKFtlbmVteVsiYm9keSJdWzBdWyJ4Il0sIGVuZW15WyJib2R5Il1bMF1bInkiXV0pCiAgICAgICAgICAgICAgICBlbmVteV9sZW5ndGggPSBlbmVteVsibGVuZ3RoIl0KCiAgICAgICAgICAgICAgICBpZiBlbmVteV9sZW5ndGggPT0gMDoKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgICAgIGVuZW15X2JvZHlfc2V0ID0geyhzZWdbIngiXSwgc2VnWyJ5Il0pIGZvciBzZWcgaW4gZW5lbXlbImJvZHkiXX0KCiAgICAgICAgICAgICAgICBpZiBuZXh0X2hlYWQgaW4gZW5lbXlfYm9keV9zZXQ6CiAgICAgICAgICAgICAgICAgICAgdmV0byA9IFRydWUKICAgICAgICAgICAgICAgICAgICBicmVhawoKICAgICAgICAgICAgICAgIGVuZW15X2Nhbl9yZWFjaCA9IHNldCgpCiAgICAgICAgICAgICAgICBmb3IgZW1vdmUgaW4gWygidXAiLCAwLCAxKSwgKCJkb3duIiwgMCwgLTEpLCAoImxlZnQiLCAtMSwgMCksICgicmlnaHQiLCAxLCAwKV06CiAgICAgICAgICAgICAgICAgICAgZXgsIGV5ID0gZW5lbXlfaGVhZFswXSArIGVtb3ZlWzFdLCBlbmVteV9oZWFkWzFdICsgZW1vdmVbMl0KICAgICAgICAgICAgICAgICAgICBpZiAwIDw9IGV4IDwgYm9hcmRbIndpZHRoIl0gYW5kIDAgPD0gZXkgPCBib2FyZFsiaGVpZ2h0Il06CiAgICAgICAgICAgICAgICAgICAgICAgIGVuZW15X2Nhbl9yZWFjaC5hZGQoKGV4LCBleSkpCgogICAgICAgICAgICAgICAgaWYgbmV4dF9oZWFkIGluIGVuZW15X2Nhbl9yZWFjaDoKICAgICAgICAgICAgICAgICAgICBpZiBlbmVteV9sZW5ndGggPj0gbXlfbGVuZ3RoOgogICAgICAgICAgICAgICAgICAgICAgICB2ZXRvID0gVHJ1ZQogICAgICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgICAgIHNjb3JlX3ZhbCArPSA1LjAKCiAgICAgICAgICAgIGlmIHZldG86CiAgICAgICAgICAgICAgICByZXN1bHRbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgZWxpZiBkaXJlY3Rpb24gbm90IGluIHJlc3VsdDoKICAgICAgICAgICAgICAgIHJlc3VsdFtkaXJlY3Rpb25dID0gc2NvcmVfdmFsCgogICAgICAgIHJldHVybiByZXN1bHQKICAgIGV4Y2VwdDoKICAgICAgICByZXR1cm4geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9Cg==', 'endgame': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHRyeToKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlWyJ5b3UiXQogICAgICAgIGJvYXJkID0gZ2FtZV9zdGF0ZVsiYm9hcmQiXQogICAgICAgIHlvdXJfaGVhZCA9ICh5b3VbImJvZHkiXVswXVsieCJdLCB5b3VbImJvZHkiXVswXVsieSJdKQogICAgICAgIHlvdXJfbGVuZ3RoID0geW91WyJsZW5ndGgiXQogICAgICAgIHdpZHRoLCBoZWlnaHQgPSBib2FyZFsid2lkdGgiXSwgYm9hcmRbImhlaWdodCJdCgogICAgICAgIHlvdXJfYm9keV9zZXQgPSBzZXQoKHNlZ1sieCJdLCBzZWdbInkiXSkgZm9yIHNlZyBpbiB5b3VbImJvZHkiXSkKICAgICAgICB5b3VyX3RhaWwgPSAoeW91WyJib2R5Il1bLTFdWyJ4Il0sIHlvdVsiYm9keSJdWy0xXVsieSJdKQoKICAgICAgICBlbmVteV9zbmFrZXMgPSBbcyBmb3IgcyBpbiBib2FyZFsic25ha2VzIl0gaWYgc1siaWQiXSAhPSB5b3VbImlkIl1dCgogICAgICAgIGRlZiBmbG9vZF9maWxsKHN0YXJ0LCBleGNsdWRlKToKICAgICAgICAgICAgdmlzaXRlZCA9IHNldChbc3RhcnRdKQogICAgICAgICAgICBxID0gZGVxdWUoW3N0YXJ0XSkKICAgICAgICAgICAgd2hpbGUgcToKICAgICAgICAgICAgICAgIHgsIHkgPSBxLnBvcGxlZnQoKQogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0IGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZCBhbmQgKG54LCBueSkgbm90IGluIGV4Y2x1ZGU6CiAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICBxLmFwcGVuZCgobngsIG55KSkKICAgICAgICAgICAgcmV0dXJuIHZpc2l0ZWQKCiAgICAgICAgZGVmIHJlYWNoYWJsZV9hZnRlcihoZWFkLCBpc19ncm93aW5nKToKICAgICAgICAgICAgZnV0dXJlX2JvZHkgPSBzZXQoKHNlZ1sieCJdLCBzZWdbInkiXSkgZm9yIHNlZyBpbiB5b3VbImJvZHkiXVs6LTFdKSBpZiBub3QgaXNfZ3Jvd2luZyBlbHNlIHlvdXJfYm9keV9zZXQKICAgICAgICAgICAgaWYgaGVhZCBpbiBmdXR1cmVfYm9keToKICAgICAgICAgICAgICAgIHJldHVybiBzZXQoKQogICAgICAgICAgICByZXR1cm4gZmxvb2RfZmlsbChoZWFkLCBmdXR1cmVfYm9keSkKCiAgICAgICAgcmVzdWx0ID0ge30KICAgICAgICBtb3ZlcyA9IHsidXAiOiAoMCwgMSksICJkb3duIjogKDAsIC0xKSwgImxlZnQiOiAoLTEsIDApLCAicmlnaHQiOiAoMSwgMCl9CgogICAgICAgIGZvciBtb3ZlX25hbWUsIChkeCwgZHkpIGluIG1vdmVzLml0ZW1zKCk6CiAgICAgICAgICAgIG54LCBueSA9IHlvdXJfaGVhZFswXSArIGR4LCB5b3VyX2hlYWRbMV0gKyBkeQoKICAgICAgICAgICAgaWYgbm90ICgwIDw9IG54IDwgd2lkdGggYW5kIDAgPD0gbnkgPCBoZWlnaHQpOgogICAgICAgICAgICAgICAgcmVzdWx0W21vdmVfbmFtZV0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgaWYgKG54LCBueSkgaW4geW91cl9ib2R5X3NldDoKICAgICAgICAgICAgICAgIHJlc3VsdFttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIG5ld19oZWFkID0gKG54LCBueSkKCiAgICAgICAgICAgIGlmIGFueShzWyJsZW5ndGgiXSA+PSB5b3VyX2xlbmd0aCBhbmQgYW55KChzWyJib2R5Il1bMF1bIngiXSArIGRkeCwgc1siYm9keSJdWzBdWyJ5Il0gKyBkZHkpID09IG5ld19oZWFkIGZvciBkZHgsIGRkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldKSBmb3IgcyBpbiBlbmVteV9zbmFrZXMpOgogICAgICAgICAgICAgICAgcmVzdWx0W21vdmVfbmFtZV0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgaXNfZWF0aW5nID0gYW55KG5ld19oZWFkID09IChmWyJ4Il0sIGZbInkiXSkgZm9yIGYgaW4gYm9hcmQuZ2V0KCJmb29kIiwgW10pKQogICAgICAgICAgICByZWFjaGFibGUgPSByZWFjaGFibGVfYWZ0ZXIobmV3X2hlYWQsIGlzX2VhdGluZykKCiAgICAgICAgICAgIGlmIGxlbihyZWFjaGFibGUpIDwgeW91cl9sZW5ndGg6CiAgICAgICAgICAgICAgICByZXN1bHRbbW92ZV9uYW1lXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBzY29yZV92YWwgPSAwLjAKCiAgICAgICAgICAgIGNlbnRlcl94LCBjZW50ZXJfeSA9IHdpZHRoIC8gMi4wLCBoZWlnaHQgLyAyLjAKICAgICAgICAgICAgZGlzdF90b19jZW50ZXIgPSBhYnMobnggLSBjZW50ZXJfeCkgKyBhYnMobnkgLSBjZW50ZXJfeSkKICAgICAgICAgICAgc2NvcmVfdmFsIC09IGRpc3RfdG9fY2VudGVyICogMC4xNQoKICAgICAgICAgICAgaWYgbGVuKGVuZW15X3NuYWtlcykgPj0gMToKICAgICAgICAgICAgICAgIGVuZW15ID0gZW5lbXlfc25ha2VzWzBdCiAgICAgICAgICAgICAgICBlbmVteV9sZW5ndGggPSBlbmVteVsibGVuZ3RoIl0KCiAgICAgICAgICAgICAgICBpZiB5b3VyX2xlbmd0aCA+IGVuZW15X2xlbmd0aDoKICAgICAgICAgICAgICAgICAgICBzY29yZV92YWwgKz0gOC4wCiAgICAgICAgICAgICAgICAgICAgb3Bwb25lbnRfYm9keSA9IHNldCgoc2VnWyJ4Il0sIHNlZ1sieSJdKSBmb3Igc2VnIGluIGVuZW15WyJib2R5Il0pCiAgICAgICAgICAgICAgICAgICAgb3Bwb25lbnRfcmVhY2hhYmxlID0gZmxvb2RfZmlsbCgoZW5lbXlbImJvZHkiXVswXVsieCJdLCBlbmVteVsiYm9keSJdWzBdWyJ5Il0pLCBvcHBvbmVudF9ib2R5KQogICAgICAgICAgICAgICAgICAgIHNwYWNlX3NocmluayA9IDUwLjAgLSBsZW4ob3Bwb25lbnRfcmVhY2hhYmxlKSAqIDAuMwogICAgICAgICAgICAgICAgICAgIHNjb3JlX3ZhbCArPSBtYXgoMCwgc3BhY2Vfc2hyaW5rKQogICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICBzY29yZV92YWwgLT0gMi4wCiAgICAgICAgICAgICAgICAgICAgc2NvcmVfdmFsICs9IGxlbihyZWFjaGFibGUpICogMC4xCgogICAgICAgICAgICByZXN1bHRbbW92ZV9uYW1lXSA9IHNjb3JlX3ZhbAoKICAgICAgICByZXR1cm4gcmVzdWx0CiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQo=', 'space_control': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHRyeToKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlWyJ5b3UiXQogICAgICAgIGJvYXJkID0gZ2FtZV9zdGF0ZVsiYm9hcmQiXQogICAgICAgIHlvdXJfaGVhZCA9ICh5b3VbImJvZHkiXVswXVsieCJdLCB5b3VbImJvZHkiXVswXVsieSJdKQogICAgICAgIHlvdXJfbGVuZ3RoID0geW91WyJsZW5ndGgiXQogICAgICAgIHdpZHRoLCBoZWlnaHQgPSBib2FyZFsid2lkdGgiXSwgYm9hcmRbImhlaWdodCJdCgogICAgICAgIHlvdXJfYm9keV9zZXQgPSBzZXQoKHNlZ1sieCJdLCBzZWdbInkiXSkgZm9yIHNlZyBpbiB5b3VbImJvZHkiXSkKICAgICAgICB5b3VyX3RhaWwgPSAoeW91WyJib2R5Il1bLTFdWyJ4Il0sIHlvdVsiYm9keSJdWy0xXVsieSJdKQoKICAgICAgICBlbmVteV9zbmFrZXMgPSBbcyBmb3IgcyBpbiBib2FyZFsic25ha2VzIl0gaWYgc1siaWQiXSAhPSB5b3VbImlkIl1dCgogICAgICAgIGRlZiBmbG9vZF9maWxsKHN0YXJ0LCBleGNsdWRlKToKICAgICAgICAgICAgdmlzaXRlZCA9IHNldChbc3RhcnRdKQogICAgICAgICAgICBxID0gZGVxdWUoW3N0YXJ0XSkKICAgICAgICAgICAgd2hpbGUgcToKICAgICAgICAgICAgICAgIHgsIHkgPSBxLnBvcGxlZnQoKQogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0IGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZCBhbmQgKG54LCBueSkgbm90IGluIGV4Y2x1ZGU6CiAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICBxLmFwcGVuZCgobngsIG55KSkKICAgICAgICAgICAgcmV0dXJuIHZpc2l0ZWQKCiAgICAgICAgZGVmIHJlYWNoYWJsZV9hZnRlcihoZWFkLCBpc19ncm93aW5nKToKICAgICAgICAgICAgZnV0dXJlX2JvZHkgPSBzZXQoKHNlZ1sieCJdLCBzZWdbInkiXSkgZm9yIHNlZyBpbiB5b3VbImJvZHkiXVs6LTFdKSBpZiBub3QgaXNfZ3Jvd2luZyBlbHNlIHlvdXJfYm9keV9zZXQKICAgICAgICAgICAgaWYgaGVhZCBpbiBmdXR1cmVfYm9keToKICAgICAgICAgICAgICAgIHJldHVybiBzZXQoKQogICAgICAgICAgICByZXR1cm4gZmxvb2RfZmlsbChoZWFkLCBmdXR1cmVfYm9keSkKCiAgICAgICAgZm9vZF9saXN0ID0gYm9hcmQuZ2V0KCJmb29kIiwgW10pCiAgICAgICAgZm9vZF9wb3NpdGlvbnMgPSB7KGZbIngiXSwgZlsieSJdKSBmb3IgZiBpbiBmb29kX2xpc3R9CgogICAgICAgIHJlc3VsdCA9IHt9CiAgICAgICAgbW92ZXMgPSB7InVwIjogKDAsIDEpLCAiZG93biI6ICgwLCAtMSksICJsZWZ0IjogKC0xLCAwKSwgInJpZ2h0IjogKDEsIDApfQoKICAgICAgICBmb3IgbW92ZV9uYW1lLCAoZHgsIGR5KSBpbiBtb3Zlcy5pdGVtcygpOgogICAgICAgICAgICBueCwgbnkgPSB5b3VyX2hlYWRbMF0gKyBkeCwgeW91cl9oZWFkWzFdICsgZHkKCiAgICAgICAgICAgIGlmIG5vdCAoMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0KToKICAgICAgICAgICAgICAgIHJlc3VsdFttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlmIChueCwgbnkpIGluIHlvdXJfYm9keV9zZXQ6CiAgICAgICAgICAgICAgICByZXN1bHRbbW92ZV9uYW1lXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBuZXdfaGVhZCA9IChueCwgbnkpCgogICAgICAgICAgICBpZiBhbnkoc1sibGVuZ3RoIl0gPj0geW91cl9sZW5ndGggYW5kIGFueSgoc1siYm9keSJdWzBdWyJ4Il0gKyBkZHgsIHNbImJvZHkiXVswXVsieSJdICsgZGR5KSA9PSBuZXdfaGVhZCBmb3IgZGR4LCBkZHkgaW4gWygwLCAxKSwgKDAsIC0xKSwgKDEsIDApLCAoLTEsIDApXSkgZm9yIHMgaW4gZW5lbXlfc25ha2VzKToKICAgICAgICAgICAgICAgIHJlc3VsdFttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlzX2VhdGluZyA9IG5ld19oZWFkIGluIGZvb2RfcG9zaXRpb25zCiAgICAgICAgICAgIHJlYWNoYWJsZSA9IHJlYWNoYWJsZV9hZnRlcihuZXdfaGVhZCwgaXNfZWF0aW5nKQoKICAgICAgICAgICAgaWYgbGVuKHJlYWNoYWJsZSkgPCB5b3VyX2xlbmd0aDoKICAgICAgICAgICAgICAgIHJlc3VsdFttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIHNjb3JlX3ZhbCA9IDAuMAoKICAgICAgICAgICAgIyBTdHJvbmcgZm9vZCBhdHRyYWN0aW9uIChjbG9zZXN0IGZvb2QpCiAgICAgICAgICAgIGlmIGZvb2RfcG9zaXRpb25zOgogICAgICAgICAgICAgICAgbWluX2Zvb2RfZGlzdCA9IG1pbihhYnMobnggLSBmeCkgKyBhYnMobnkgLSBmeSkgZm9yIGZ4LCBmeSBpbiBmb29kX3Bvc2l0aW9ucykKICAgICAgICAgICAgICAgIHNjb3JlX3ZhbCArPSAyMC4wIC0gbWluX2Zvb2RfZGlzdCAqIDAuNQogICAgICAgICAgICAgICAgaWYgaXNfZWF0aW5nOgogICAgICAgICAgICAgICAgICAgIHNjb3JlX3ZhbCArPSAzMC4wCgogICAgICAgICAgICAjIENlbnRlciB0ZW5kZW5jeSAocmVkdWNlZCB3ZWlnaHQpCiAgICAgICAgICAgIGNlbnRlcl94LCBjZW50ZXJfeSA9IHdpZHRoIC8gMi4wLCBoZWlnaHQgLyAyLjAKICAgICAgICAgICAgZGlzdF90b19jZW50ZXIgPSBhYnMobnggLSBjZW50ZXJfeCkgKyBhYnMobnkgLSBjZW50ZXJfeSkKICAgICAgICAgICAgc2NvcmVfdmFsIC09IGRpc3RfdG9fY2VudGVyICogMC4wNQoKICAgICAgICAgICAgaWYgbGVuKGVuZW15X3NuYWtlcykgPj0gMToKICAgICAgICAgICAgICAgIGVuZW15ID0gZW5lbXlfc25ha2VzWzBdCiAgICAgICAgICAgICAgICBlbmVteV9sZW5ndGggPSBlbmVteVsibGVuZ3RoIl0KCiAgICAgICAgICAgICAgICBpZiB5b3VyX2xlbmd0aCA+IGVuZW15X2xlbmd0aDoKICAgICAgICAgICAgICAgICAgICBzY29yZV92YWwgKz0gOC4wCiAgICAgICAgICAgICAgICAgICAgb3Bwb25lbnRfYm9keSA9IHNldCgoc2VnWyJ4Il0sIHNlZ1sieSJdKSBmb3Igc2VnIGluIGVuZW15WyJib2R5Il0pCiAgICAgICAgICAgICAgICAgICAgb3Bwb25lbnRfcmVhY2hhYmxlID0gZmxvb2RfZmlsbCgoZW5lbXlbImJvZHkiXVswXVsieCJdLCBlbmVteVsiYm9keSJdWzBdWyJ5Il0pLCBvcHBvbmVudF9ib2R5KQogICAgICAgICAgICAgICAgICAgIHNwYWNlX3NocmluayA9IDUwLjAgLSBsZW4ob3Bwb25lbnRfcmVhY2hhYmxlKSAqIDAuMwogICAgICAgICAgICAgICAgICAgIHNjb3JlX3ZhbCArPSBtYXgoMCwgc3BhY2Vfc2hyaW5rKQogICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICBzY29yZV92YWwgLT0gMi4wCiAgICAgICAgICAgICAgICAgICAgc2NvcmVfdmFsICs9IGxlbihyZWFjaGFibGUpICogMC4xCgogICAgICAgICAgICByZXN1bHRbbW92ZV9uYW1lXSA9IHNjb3JlX3ZhbAoKICAgICAgICByZXR1cm4gcmVzdWx0CiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQo='}
_PRIORITY = ['combat', 'endgame', 'space_control']
_POLICY = 'weighted_vote'
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
