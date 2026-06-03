# AUTO-ASSEMBLED decomposition bot (genotype g01_02, gen 1).
# referee_policy=weighted_vote | specialists=['space_control', 'food', 'combat'] | tester=True | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'space_control': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlWyJib2FyZCJdCiAgICAgICAgd2lkdGgsIGhlaWdodCA9IGJvYXJkWyJ3aWR0aCJdLCBib2FyZFsiaGVpZ2h0Il0KICAgICAgICBoZWFkID0geW91WyJib2R5Il1bMF0KICAgICAgICBteV9sZW5ndGggPSB5b3VbImxlbmd0aCJdCiAgICAgICAganVzdF9hdGUgPSBsZW4oeW91WyJib2R5Il0pID4gMSBhbmQgeW91WyJib2R5Il1bLTFdID09IHlvdVsiYm9keSJdWy0yXQoKICAgICAgICBib2R5X3NldCA9IHNldCgoc2VnWyJ4Il0sIHNlZ1sieSJdKSBmb3Igc2VnIGluIHlvdVsiYm9keSJdKQogICAgICAgIGlmIG5vdCBqdXN0X2F0ZSBhbmQgYm9keV9zZXQ6CiAgICAgICAgICAgIGJvZHlfc2V0LmRpc2NhcmQoKHlvdVsiYm9keSJdWy0xXVsieCJdLCB5b3VbImJvZHkiXVstMV1bInkiXSkpCgogICAgICAgIHNuYWtlX2JvZGllcyA9IHNldCgpCiAgICAgICAgZm9yIHNuYWtlIGluIGJvYXJkWyJzbmFrZXMiXToKICAgICAgICAgICAgaWYgc25ha2VbImlkIl0gIT0geW91WyJpZCJdOgogICAgICAgICAgICAgICAgZm9yIHNlZyBpbiBzbmFrZVsiYm9keSJdOgogICAgICAgICAgICAgICAgICAgIHNuYWtlX2JvZGllcy5hZGQoKHNlZ1sieCJdLCBzZWdbInkiXSkpCgogICAgICAgIGRlZiBmbG9vZF9maWxsKHN0YXJ0X3gsIHN0YXJ0X3ksIGF2b2lkX3NldCk6CiAgICAgICAgICAgIHZpc2l0ZWQgPSBzZXQoKQogICAgICAgICAgICBzdGFjayA9IFsoc3RhcnRfeCwgc3RhcnRfeSldCiAgICAgICAgICAgIHdoaWxlIHN0YWNrOgogICAgICAgICAgICAgICAgeCwgeSA9IHN0YWNrLnBvcCgpCiAgICAgICAgICAgICAgICBpZiAoeCwgeSkgaW4gdmlzaXRlZDoKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgaWYgeCA8IDAgb3IgeCA+PSB3aWR0aCBvciB5IDwgMCBvciB5ID49IGhlaWdodDoKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgaWYgKHgsIHkpIGluIGF2b2lkX3NldDoKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgdmlzaXRlZC5hZGQoKHgsIHkpKQogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIHN0YWNrLmFwcGVuZCgoeCArIGR4LCB5ICsgZHkpKQogICAgICAgICAgICByZXR1cm4gbGVuKHZpc2l0ZWQpCgogICAgICAgIG1vdmVzID0geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9CiAgICAgICAgZGVsdGFzID0geyJ1cCI6ICgwLCAxKSwgImRvd24iOiAoMCwgLTEpLCAibGVmdCI6ICgtMSwgMCksICJyaWdodCI6ICgxLCAwKX0KCiAgICAgICAgZm9yIGRpcmVjdGlvbiwgKGR4LCBkeSkgaW4gZGVsdGFzLml0ZW1zKCk6CiAgICAgICAgICAgIG5ld194LCBuZXdfeSA9IGhlYWRbIngiXSArIGR4LCBoZWFkWyJ5Il0gKyBkeQoKICAgICAgICAgICAgaWYgbmV3X3ggPCAwIG9yIG5ld194ID49IHdpZHRoIG9yIG5ld195IDwgMCBvciBuZXdfeSA+PSBoZWlnaHQ6CiAgICAgICAgICAgICAgICBtb3Zlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlmIChuZXdfeCwgbmV3X3kpIGluIGJvZHlfc2V0IG9yIChuZXdfeCwgbmV3X3kpIGluIHNuYWtlX2JvZGllczoKICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgYXZvaWRfc2V0ID0gYm9keV9zZXQgfCBzbmFrZV9ib2RpZXMKICAgICAgICAgICAgcmVhY2hhYmxlID0gZmxvb2RfZmlsbChuZXdfeCwgbmV3X3ksIGF2b2lkX3NldCkKCiAgICAgICAgICAgIGlmIHJlYWNoYWJsZSA8IG15X2xlbmd0aDoKICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICBtb3Zlc1tkaXJlY3Rpb25dID0gZmxvYXQocmVhY2hhYmxlKSAqIDAuOTUKCiAgICAgICAgcmV0dXJuIG1vdmVzCiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQo=', 'food': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlWyJib2FyZCJdCiAgICAgICAgaGVhZCA9IHR1cGxlKCh5b3VbImJvZHkiXVswXVsieCJdLCB5b3VbImJvZHkiXVswXVsieSJdKSkKICAgICAgICBoZWFsdGggPSB5b3VbImhlYWx0aCJdCiAgICAgICAgbGVuZ3RoID0geW91WyJsZW5ndGgiXQogICAgICAgIHdpZHRoLCBoZWlnaHQgPSBib2FyZFsid2lkdGgiXSwgYm9hcmRbImhlaWdodCJdCiAgICAgICAgZm9vZF9saXN0ID0gWyhmWyJ4Il0sIGZbInkiXSkgZm9yIGYgaW4gYm9hcmRbImZvb2QiXV0KICAgICAgICBoYXphcmRzID0geyhoWyJ4Il0sIGhbInkiXSkgZm9yIGggaW4gYm9hcmRbImhhemFyZHMiXX0KICAgICAgICBzbmFrZV9ib2RpZXMgPSBzZXQoKQogICAgICAgIGZvciBzbmFrZSBpbiBib2FyZFsic25ha2VzIl06CiAgICAgICAgICAgIGZvciBzZWdtZW50IGluIHNuYWtlWyJib2R5Il06CiAgICAgICAgICAgICAgICBzbmFrZV9ib2RpZXMuYWRkKChzZWdtZW50WyJ4Il0sIHNlZ21lbnRbInkiXSkpCiAgICAgICAgc25ha2VfYm9kaWVzLmRpc2NhcmQoaGVhZCkKICAgICAgICB0YWlsID0gdHVwbGUoKHlvdVsiYm9keSJdWy0xXVsieCJdLCB5b3VbImJvZHkiXVstMV1bInkiXSkpCiAgICAgICAgaWYgbGVuKHlvdVsiYm9keSJdKSA+IDE6CiAgICAgICAgICAgIHNuYWtlX2JvZGllcy5kaXNjYXJkKHRhaWwpCgogICAgICAgIGxvbmdlc3RfbGVuZ3RoID0gbWF4KFtzWyJsZW5ndGgiXSBmb3IgcyBpbiBib2FyZFsic25ha2VzIl1dLCBkZWZhdWx0PTApCiAgICAgICAgaXNfbG9uZ2VzdCA9IGxlbmd0aCA+PSBsb25nZXN0X2xlbmd0aAogICAgICAgIHNob3VsZF9zZWVrX2Zvb2QgPSBoZWFsdGggPCA0MCBvciBub3QgaXNfbG9uZ2VzdAoKICAgICAgICBkZWYgYmZzX3JlYWNoYWJsZShzdGFydCwgYXZvaWRfY2VsbHMsIG1heF9zdGVwcz0xMDApOgogICAgICAgICAgICBmcm9tIGNvbGxlY3Rpb25zIGltcG9ydCBkZXF1ZQogICAgICAgICAgICB2aXNpdGVkLCBxdWV1ZSA9IHtzdGFydH0sIGRlcXVlKFsoc3RhcnQsIDApXSkKICAgICAgICAgICAgd2hpbGUgcXVldWU6CiAgICAgICAgICAgICAgICAoeCwgeSksIGRpc3QgPSBxdWV1ZS5wb3BsZWZ0KCkKICAgICAgICAgICAgICAgIGlmIGRpc3QgPj0gbWF4X3N0ZXBzOgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICBmb3IgZHgsIGR5IGluIFsoMCwgMSksICgwLCAtMSksICgxLCAwKSwgKC0xLCAwKV06CiAgICAgICAgICAgICAgICAgICAgbngsIG55ID0geCArIGR4LCB5ICsgZHkKICAgICAgICAgICAgICAgICAgICBpZiAwIDw9IG54IDwgd2lkdGggYW5kIDAgPD0gbnkgPCBoZWlnaHQgYW5kIChueCwgbnkpIG5vdCBpbiB2aXNpdGVkIGFuZCAobngsIG55KSBub3QgaW4gYXZvaWRfY2VsbHM6CiAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICBxdWV1ZS5hcHBlbmQoKChueCwgbnkpLCBkaXN0ICsgMSkpCiAgICAgICAgICAgIHJldHVybiB2aXNpdGVkCgogICAgICAgIGRlZiBuZWFyZXN0X2Zvb2RfZGlzdGFuY2Uoc3RhcnQsIGZvb2RfY2VsbHMsIGF2b2lkKToKICAgICAgICAgICAgZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKICAgICAgICAgICAgdmlzaXRlZCwgcXVldWUgPSB7c3RhcnR9LCBkZXF1ZShbKHN0YXJ0LCAwKV0pCiAgICAgICAgICAgIHdoaWxlIHF1ZXVlOgogICAgICAgICAgICAgICAgKHgsIHkpLCBkaXN0ID0gcXVldWUucG9wbGVmdCgpCiAgICAgICAgICAgICAgICBpZiAoeCwgeSkgaW4gZm9vZF9jZWxsczoKICAgICAgICAgICAgICAgICAgICByZXR1cm4gZGlzdAogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0IGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZCBhbmQgKG54LCBueSkgbm90IGluIGF2b2lkOgogICAgICAgICAgICAgICAgICAgICAgICB2aXNpdGVkLmFkZCgobngsIG55KSkKICAgICAgICAgICAgICAgICAgICAgICAgcXVldWUuYXBwZW5kKCgobngsIG55KSwgZGlzdCArIDEpKQogICAgICAgICAgICByZXR1cm4gZmxvYXQoJ2luZicpCgogICAgICAgIGRlZiBpc19kZWFkX2VuZChjZWxsLCBhdm9pZCk6CiAgICAgICAgICAgIHJlYWNoYWJsZSA9IGJmc19yZWFjaGFibGUoY2VsbCwgYXZvaWQsIG1heF9zdGVwcz1sZW5ndGggKyA1KQogICAgICAgICAgICByZXR1cm4gbGVuKHJlYWNoYWJsZSkgPCBsZW5ndGgKCiAgICAgICAgc2NvcmVzID0geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9CiAgICAgICAgbW92ZXMgPSB7InVwIjogKDAsIDEpLCAiZG93biI6ICgwLCAtMSksICJsZWZ0IjogKC0xLCAwKSwgInJpZ2h0IjogKDEsIDApfQoKICAgICAgICBmb3IgZGlyZWN0aW9uLCAoZHgsIGR5KSBpbiBtb3Zlcy5pdGVtcygpOgogICAgICAgICAgICBueCwgbnkgPSBoZWFkWzBdICsgZHgsIGhlYWRbMV0gKyBkeQogICAgICAgICAgICBpZiBub3QgKDAgPD0gbnggPCB3aWR0aCBhbmQgMCA8PSBueSA8IGhlaWdodCk6CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIGlmIChueCwgbnkpIGluIHNuYWtlX2JvZGllczoKICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIG5ld19hdm9pZCA9IHNuYWtlX2JvZGllcy5jb3B5KCkKICAgICAgICAgICAgaWYgKG54LCBueSkgIT0gdGFpbDoKICAgICAgICAgICAgICAgIG5ld19hdm9pZC5hZGQodGFpbCkKCiAgICAgICAgICAgIGlmIG5vdCBzaG91bGRfc2Vla19mb29kOgogICAgICAgICAgICAgICAgc2NvcmVzW2RpcmVjdGlvbl0gPSAwLjAKICAgICAgICAgICAgZWxpZiBub3QgZm9vZF9saXN0OgogICAgICAgICAgICAgICAgc2NvcmVzW2RpcmVjdGlvbl0gPSAwLjAKICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgIGNsb3Nlc3RfZGlzdCA9IGZsb2F0KCdpbmYnKQogICAgICAgICAgICAgICAgZm9yIGZ4LCBmeSBpbiBmb29kX2xpc3Q6CiAgICAgICAgICAgICAgICAgICAgaWYgaXNfZGVhZF9lbmQoKGZ4LCBmeSksIG5ld19hdm9pZCk6CiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgZGlzdCA9IG5lYXJlc3RfZm9vZF9kaXN0YW5jZSgobngsIG55KSwgeyhmeCwgZnkpfSwgbmV3X2F2b2lkKQogICAgICAgICAgICAgICAgICAgIGNsb3Nlc3RfZGlzdCA9IG1pbihjbG9zZXN0X2Rpc3QsIGRpc3QpCiAgICAgICAgICAgICAgICBpZiBjbG9zZXN0X2Rpc3QgPT0gZmxvYXQoJ2luZicpOgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gLTAuNQogICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IG1heCgwLjAsIDEwLjAgLSBjbG9zZXN0X2Rpc3QgKiAwLjUpCgogICAgICAgIHJldHVybiBzY29yZXMKICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQo=', 'combat': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlWyJib2FyZCJdCiAgICAgICAgeW91cl9oZWFkID0gKHlvdVsiYm9keSJdWzBdWyJ4Il0sIHlvdVsiYm9keSJdWzBdWyJ5Il0pCiAgICAgICAgeW91cl9sZW5ndGggPSB5b3VbImxlbmd0aCJdCgogICAgICAgIG1vdmVzID0geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9CiAgICAgICAgZGlyZWN0aW9ucyA9IHsidXAiOiAoMCwgMSksICJkb3duIjogKDAsIC0xKSwgImxlZnQiOiAoLTEsIDApLCAicmlnaHQiOiAoMSwgMCl9CiAgICAgICAgeW91cl9ib2R5X2NlbGxzID0gc2V0KChiWyJ4Il0sIGJbInkiXSkgZm9yIGIgaW4geW91WyJib2R5Il0pCgogICAgICAgIGZvciBtb3ZlLCAoZHgsIGR5KSBpbiBkaXJlY3Rpb25zLml0ZW1zKCk6CiAgICAgICAgICAgIG5ld194LCBuZXdfeSA9IHlvdXJfaGVhZFswXSArIGR4LCB5b3VyX2hlYWRbMV0gKyBkeQogICAgICAgICAgICBuZXdfaGVhZCA9IChuZXdfeCwgbmV3X3kpCgogICAgICAgICAgICBpZiBuZXdfeCA8IDAgb3IgbmV3X3ggPj0gYm9hcmRbIndpZHRoIl0gb3IgbmV3X3kgPCAwIG9yIG5ld195ID49IGJvYXJkWyJoZWlnaHQiXToKICAgICAgICAgICAgICAgIG1vdmVzW21vdmVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlmIG5ld19oZWFkIGluIHlvdXJfYm9keV9jZWxsczoKICAgICAgICAgICAgICAgIG1vdmVzW21vdmVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGRhbmdlcm91cyA9IEZhbHNlCiAgICAgICAgICAgIHdpbl9ib251cyA9IDAuMAogICAgICAgICAgICB2dWxuZXJhYmlsaXR5X3BlbmFsdHkgPSAwLjAKCiAgICAgICAgICAgIGZvciBlbmVteSBpbiBib2FyZFsic25ha2VzIl06CiAgICAgICAgICAgICAgICBpZiBlbmVteVsiaWQiXSA9PSB5b3VbImlkIl06CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICAgICBlbmVteV9oZWFkID0gKGVuZW15WyJib2R5Il1bMF1bIngiXSwgZW5lbXlbImJvZHkiXVswXVsieSJdKQogICAgICAgICAgICAgICAgZW5lbXlfbGVuZ3RoID0gZW5lbXlbImxlbmd0aCJdCiAgICAgICAgICAgICAgICBlbmVteV9ib2R5X2NlbGxzID0gc2V0KChiWyJ4Il0sIGJbInkiXSkgZm9yIGIgaW4gZW5lbXlbImJvZHkiXSkKCiAgICAgICAgICAgICAgICBpZiBuZXdfaGVhZCBpbiBlbmVteV9ib2R5X2NlbGxzOgogICAgICAgICAgICAgICAgICAgIG1vdmVzW21vdmVdID0gLTFlOQogICAgICAgICAgICAgICAgICAgIGRhbmdlcm91cyA9IFRydWUKICAgICAgICAgICAgICAgICAgICBicmVhawoKICAgICAgICAgICAgICAgIGVuZW15X3JlYWNoYWJsZSA9IHNldCgpCiAgICAgICAgICAgICAgICBmb3IgZW0sIChlZHgsIGVkeSkgaW4gZGlyZWN0aW9ucy5pdGVtcygpOgogICAgICAgICAgICAgICAgICAgIG5leHRfeCwgbmV4dF95ID0gZW5lbXlfaGVhZFswXSArIGVkeCwgZW5lbXlfaGVhZFsxXSArIGVkeQogICAgICAgICAgICAgICAgICAgIGlmIDAgPD0gbmV4dF94IDwgYm9hcmRbIndpZHRoIl0gYW5kIDAgPD0gbmV4dF95IDwgYm9hcmRbImhlaWdodCJdOgogICAgICAgICAgICAgICAgICAgICAgICBlbmVteV9yZWFjaGFibGUuYWRkKChuZXh0X3gsIG5leHRfeSkpCgogICAgICAgICAgICAgICAgaWYgbmV3X2hlYWQgaW4gZW5lbXlfcmVhY2hhYmxlOgogICAgICAgICAgICAgICAgICAgIGlmIGVuZW15X2xlbmd0aCA+PSB5b3VyX2xlbmd0aDoKICAgICAgICAgICAgICAgICAgICAgICAgZGFuZ2Vyb3VzID0gVHJ1ZQogICAgICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgICAgIHdpbl9ib251cyArPSAyLjAKICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgaWYgZW5lbXlfbGVuZ3RoID4geW91cl9sZW5ndGg6CiAgICAgICAgICAgICAgICAgICAgICAgIHR3b19tb3ZlX3JlYWNoID0gZW5lbXlfcmVhY2hhYmxlLmNvcHkoKQogICAgICAgICAgICAgICAgICAgICAgICBmb3IgbngsIG55IGluIGxpc3QoZW5lbXlfcmVhY2hhYmxlKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZvciBlZHgsIGVkeSBpbiBkaXJlY3Rpb25zLnZhbHVlcygpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG5leHRfeCwgbmV4dF95ID0gbnggKyBlZHgsIG55ICsgZWR5CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBuZXh0X3ggPCBib2FyZFsid2lkdGgiXSBhbmQgMCA8PSBuZXh0X3kgPCBib2FyZFsiaGVpZ2h0Il06CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHR3b19tb3ZlX3JlYWNoLmFkZCgobmV4dF94LCBuZXh0X3kpKQogICAgICAgICAgICAgICAgICAgICAgICBpZiBuZXdfaGVhZCBpbiB0d29fbW92ZV9yZWFjaDoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHZ1bG5lcmFiaWxpdHlfcGVuYWx0eSAtPSAxLjAKCiAgICAgICAgICAgIGlmIGRhbmdlcm91czoKICAgICAgICAgICAgICAgIG1vdmVzW21vdmVdID0gLTFlOQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgbW92ZXNbbW92ZV0gKz0gd2luX2JvbnVzICsgdnVsbmVyYWJpbGl0eV9wZW5hbHR5CgogICAgICAgIHJldHVybiBtb3ZlcwogICAgZXhjZXB0OgogICAgICAgIHJldHVybiB7bTogMC4wIGZvciBtIGluIFsidXAiLCAiZG93biIsICJsZWZ0IiwgInJpZ2h0Il19Cg=='}
_PRIORITY = ['space_control', 'food', 'combat']
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
