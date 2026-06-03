# AUTO-ASSEMBLED decomposition bot (genotype g01_03, gen 1).
# referee_policy=weighted_vote | specialists=['space_control', 'combat', 'food'] | tester=True | refine_rounds=3
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'space_control': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIGJvYXJkID0gZ2FtZV9zdGF0ZVsiYm9hcmQiXQogICAgICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICAgICAgd2lkdGgsIGhlaWdodCA9IGJvYXJkWyJ3aWR0aCJdLCBib2FyZFsiaGVpZ2h0Il0KICAgICAgICB5b3VyX2JvZHkgPSB5b3VbImJvZHkiXQogICAgICAgIHlvdXJfbGVuZ3RoID0geW91WyJsZW5ndGgiXQogICAgICAgIHlvdXJfaGVhZCA9IHR1cGxlKCh5b3VyX2JvZHlbMF1bIngiXSwgeW91cl9ib2R5WzBdWyJ5Il0pKQogICAgICAgIHlvdXJfdGFpbCA9IHR1cGxlKCh5b3VyX2JvZHlbLTFdWyJ4Il0sIHlvdXJfYm9keVstMV1bInkiXSkpCgogICAgICAgIGJvZHlfc2V0ID0gc2V0KChzZWdbIngiXSwgc2VnWyJ5Il0pIGZvciBzZWcgaW4geW91cl9ib2R5KQogICAgICAgIGFsbF9zbmFrZV9jZWxscyA9IHNldCgpCiAgICAgICAgZm9yIHNuYWtlIGluIGJvYXJkWyJzbmFrZXMiXToKICAgICAgICAgICAgZm9yIHNlZyBpbiBzbmFrZVsiYm9keSJdOgogICAgICAgICAgICAgICAgYWxsX3NuYWtlX2NlbGxzLmFkZCgoc2VnWyJ4Il0sIHNlZ1sieSJdKSkKCiAgICAgICAgaGF6YXJkX3NldCA9IHNldCgoaFsieCJdLCBoWyJ5Il0pIGZvciBoIGluIGJvYXJkLmdldCgiaGF6YXJkcyIsIFtdKSkKCiAgICAgICAgZGVmIGZsb29kX2ZpbGwoc3RhcnQpOgogICAgICAgICAgICB2aXNpdGVkID0gc2V0KCkKICAgICAgICAgICAgcXVldWUgPSBbc3RhcnRdCiAgICAgICAgICAgIHZpc2l0ZWQuYWRkKHN0YXJ0KQogICAgICAgICAgICBjb3VudCA9IDAKICAgICAgICAgICAgd2hpbGUgcXVldWU6CiAgICAgICAgICAgICAgICB4LCB5ID0gcXVldWUucG9wKDApCiAgICAgICAgICAgICAgICBjb3VudCArPSAxCiAgICAgICAgICAgICAgICBmb3IgZHgsIGR5IGluIFsoMCwgMSksICgwLCAtMSksICgxLCAwKSwgKC0xLCAwKV06CiAgICAgICAgICAgICAgICAgICAgbngsIG55ID0geCArIGR4LCB5ICsgZHkKICAgICAgICAgICAgICAgICAgICBpZiAwIDw9IG54IDwgd2lkdGggYW5kIDAgPD0gbnkgPCBoZWlnaHQgYW5kIChueCwgbnkpIG5vdCBpbiB2aXNpdGVkOgogICAgICAgICAgICAgICAgICAgICAgICBpZiAobngsIG55KSBub3QgaW4gYWxsX3NuYWtlX2NlbGxzIG9yIChueCwgbnkpID09IHlvdXJfdGFpbDoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgcXVldWUuYXBwZW5kKChueCwgbnkpKQogICAgICAgICAgICByZXR1cm4gY291bnQKCiAgICAgICAgcmVzdWx0ID0ge30KICAgICAgICBtb3ZlcyA9IFsoInVwIiwgMCwgMSksICgiZG93biIsIDAsIC0xKSwgKCJsZWZ0IiwgLTEsIDApLCAoInJpZ2h0IiwgMSwgMCldCgogICAgICAgIGZvciBtb3ZlX25hbWUsIGR4LCBkeSBpbiBtb3ZlczoKICAgICAgICAgICAgbngsIG55ID0geW91cl9oZWFkWzBdICsgZHgsIHlvdXJfaGVhZFsxXSArIGR5CgogICAgICAgICAgICBpZiBub3QgKDAgPD0gbnggPCB3aWR0aCBhbmQgMCA8PSBueSA8IGhlaWdodCk6CiAgICAgICAgICAgICAgICByZXN1bHRbbW92ZV9uYW1lXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBpZiAobngsIG55KSBpbiBhbGxfc25ha2VfY2VsbHMgYW5kIChueCwgbnkpICE9IHlvdXJfdGFpbDoKICAgICAgICAgICAgICAgIHJlc3VsdFttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIHJlYWNoYWJsZSA9IGZsb29kX2ZpbGwoKG54LCBueSkpCgogICAgICAgICAgICBpZiByZWFjaGFibGUgPCB5b3VyX2xlbmd0aDoKICAgICAgICAgICAgICAgIHJlc3VsdFttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgcmVzdWx0W21vdmVfbmFtZV0gPSBmbG9hdChyZWFjaGFibGUpCgogICAgICAgIHJldHVybiByZXN1bHQKICAgIGV4Y2VwdDoKICAgICAgICByZXR1cm4geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9Cg==', 'combat': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgbW92ZXMgPSB7InVwIjogMC4wLCAiZG93biI6IDAuMCwgImxlZnQiOiAwLjAsICJyaWdodCI6IDAuMH0KICAgIHRyeToKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlLmdldCgieW91Iiwge30pCiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlLmdldCgiYm9hcmQiLCB7fSkKICAgICAgICB5b3VyX2JvZHkgPSB5b3UuZ2V0KCJib2R5IiwgW10pCiAgICAgICAgeW91cl9sZW5ndGggPSB5b3UuZ2V0KCJsZW5ndGgiLCAwKQogICAgICAgIHlvdXJfaGVhbHRoID0geW91LmdldCgiaGVhbHRoIiwgMCkKCiAgICAgICAgaWYgbm90IHlvdXJfYm9keToKICAgICAgICAgICAgcmV0dXJuIG1vdmVzCgogICAgICAgIGhlYWQgPSB5b3VyX2JvZHlbMF0KICAgICAgICB5b3VyX2hlYWQgPSAoaGVhZFsieCJdLCBoZWFkWyJ5Il0pCiAgICAgICAgeW91cl90YWlsID0gKHlvdXJfYm9keVstMV1bIngiXSwgeW91cl9ib2R5Wy0xXVsieSJdKSBpZiB5b3VyX2JvZHkgZWxzZSBOb25lCiAgICAgICAganVzdF9hdGUgPSBsZW4oeW91cl9ib2R5KSA+IDEgYW5kIHlvdXJfYm9keVstMV1bIngiXSA9PSB5b3VyX2JvZHlbLTJdWyJ4Il0gYW5kIHlvdXJfYm9keVstMV1bInkiXSA9PSB5b3VyX2JvZHlbLTJdWyJ5Il0KCiAgICAgICAgd2lkdGggPSBib2FyZC5nZXQoIndpZHRoIiwgMTEpCiAgICAgICAgaGVpZ2h0ID0gYm9hcmQuZ2V0KCJoZWlnaHQiLCAxMSkKCiAgICAgICAgeW91cl9ib2R5X3NldCA9IHNldCgoYlsieCJdLCBiWyJ5Il0pIGZvciBiIGluIHlvdXJfYm9keSkKICAgICAgICBpZiBub3QganVzdF9hdGUgYW5kIHlvdXJfdGFpbDoKICAgICAgICAgICAgeW91cl9ib2R5X3NldC5kaXNjYXJkKHlvdXJfdGFpbCkKCiAgICAgICAgZW5lbXlfaGVhZHMgPSBbXQogICAgICAgIGZvciBzbmFrZSBpbiBib2FyZC5nZXQoInNuYWtlcyIsIFtdKToKICAgICAgICAgICAgaWYgc25ha2UuZ2V0KCJpZCIpICE9IHlvdS5nZXQoImlkIik6CiAgICAgICAgICAgICAgICBzbmFrZV9ib2R5ID0gc25ha2UuZ2V0KCJib2R5IiwgW10pCiAgICAgICAgICAgICAgICBpZiBzbmFrZV9ib2R5OgogICAgICAgICAgICAgICAgICAgIGVuZW15X2hlYWRzLmFwcGVuZCh7CiAgICAgICAgICAgICAgICAgICAgICAgICJoZWFkIjogKHNuYWtlX2JvZHlbMF1bIngiXSwgc25ha2VfYm9keVswXVsieSJdKSwKICAgICAgICAgICAgICAgICAgICAgICAgImxlbmd0aCI6IHNuYWtlLmdldCgibGVuZ3RoIiwgMCkKICAgICAgICAgICAgICAgICAgICB9KQoKICAgICAgICBoYXphcmRzID0gc2V0KChoWyJ4Il0sIGhbInkiXSkgZm9yIGggaW4gYm9hcmQuZ2V0KCJoYXphcmRzIiwgW10pKQoKICAgICAgICBkaXJlY3Rpb25zID0gewogICAgICAgICAgICAidXAiOiAoMCwgMSksCiAgICAgICAgICAgICJkb3duIjogKDAsIC0xKSwKICAgICAgICAgICAgImxlZnQiOiAoLTEsIDApLAogICAgICAgICAgICAicmlnaHQiOiAoMSwgMCkKICAgICAgICB9CgogICAgICAgIGZvciBkaXJlY3Rpb24sIChkeCwgZHkpIGluIGRpcmVjdGlvbnMuaXRlbXMoKToKICAgICAgICAgICAgbmV4dF94ID0geW91cl9oZWFkWzBdICsgZHgKICAgICAgICAgICAgbmV4dF95ID0geW91cl9oZWFkWzFdICsgZHkKICAgICAgICAgICAgbmV4dF9wb3MgPSAobmV4dF94LCBuZXh0X3kpCgogICAgICAgICAgICBpZiBuZXh0X3ggPCAwIG9yIG5leHRfeCA+PSB3aWR0aCBvciBuZXh0X3kgPCAwIG9yIG5leHRfeSA+PSBoZWlnaHQ6CiAgICAgICAgICAgICAgICBtb3Zlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlmIG5leHRfcG9zIGluIHlvdXJfYm9keV9zZXQ6CiAgICAgICAgICAgICAgICBtb3Zlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlmIG5leHRfcG9zIGluIGhhemFyZHM6CiAgICAgICAgICAgICAgICBtb3Zlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIHNjb3JlX3ZhbCA9IDAuMAogICAgICAgICAgICBpc19zYWZlID0gVHJ1ZQoKICAgICAgICAgICAgZm9yIGVuZW15IGluIGVuZW15X2hlYWRzOgogICAgICAgICAgICAgICAgZW5lbXlfaGVhZCA9IGVuZW15WyJoZWFkIl0KICAgICAgICAgICAgICAgIGVuZW15X2xlbmd0aCA9IGVuZW15WyJsZW5ndGgiXQoKICAgICAgICAgICAgICAgIGVuZW15X2Nhbl9yZWFjaCA9IEZhbHNlCiAgICAgICAgICAgICAgICBhZGphY2VudF9tb3ZlcyA9IFsKICAgICAgICAgICAgICAgICAgICAoZW5lbXlfaGVhZFswXSArIGR4MiwgZW5lbXlfaGVhZFsxXSArIGR5MikKICAgICAgICAgICAgICAgICAgICBmb3IgZHgyLCBkeTIgaW4gWygwLCAxKSwgKDAsIC0xKSwgKC0xLCAwKSwgKDEsIDApXQogICAgICAgICAgICAgICAgXQogICAgICAgICAgICAgICAgZm9yIGFkaiBpbiBhZGphY2VudF9tb3ZlczoKICAgICAgICAgICAgICAgICAgICBpZiBhZGogPT0gbmV4dF9wb3M6CiAgICAgICAgICAgICAgICAgICAgICAgIGVuZW15X2Nhbl9yZWFjaCA9IFRydWUKICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKCiAgICAgICAgICAgICAgICBpZiBlbmVteV9jYW5fcmVhY2g6CiAgICAgICAgICAgICAgICAgICAgaWYgZW5lbXlfbGVuZ3RoID49IHlvdXJfbGVuZ3RoOgogICAgICAgICAgICAgICAgICAgICAgICBpc19zYWZlID0gRmFsc2UKICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICBzY29yZV92YWwgKz0gNS4wCgogICAgICAgICAgICBpZiBub3QgaXNfc2FmZToKICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICBtb3Zlc1tkaXJlY3Rpb25dID0gc2NvcmVfdmFsCgogICAgICAgIHJldHVybiBtb3ZlcwogICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICByZXR1cm4ge206IDAuMCBmb3IgbSBpbiBbInVwIiwgImRvd24iLCAibGVmdCIsICJyaWdodCJdfQo=', 'food': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHRyeToKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlWyJ5b3UiXQogICAgICAgIGJvYXJkID0gZ2FtZV9zdGF0ZVsiYm9hcmQiXQogICAgICAgIGhlYWQgPSB0dXBsZSh5b3VbImJvZHkiXVswXS52YWx1ZXMoKSkKICAgICAgICB5b3VyX2hlYWx0aCA9IHlvdVsiaGVhbHRoIl0KICAgICAgICB5b3VyX2xlbmd0aCA9IHlvdVsibGVuZ3RoIl0KICAgICAgICB3aWR0aCwgaGVpZ2h0ID0gYm9hcmRbIndpZHRoIl0sIGJvYXJkWyJoZWlnaHQiXQoKICAgICAgICBmb29kX2xpc3QgPSBbdHVwbGUoZi52YWx1ZXMoKSkgZm9yIGYgaW4gYm9hcmRbImZvb2QiXV0KICAgICAgICBoYXphcmRzID0ge3R1cGxlKGgudmFsdWVzKCkpIGZvciBoIGluIGJvYXJkWyJoYXphcmRzIl19CiAgICAgICAgYWxsX3NuYWtlX2JvZGllcyA9IHNldCgpCiAgICAgICAgbWF4X290aGVyX2xlbmd0aCA9IDAKICAgICAgICBmb3Igc25ha2UgaW4gYm9hcmRbInNuYWtlcyJdOgogICAgICAgICAgICBpZiBzbmFrZVsiaWQiXSAhPSB5b3VbImlkIl06CiAgICAgICAgICAgICAgICBtYXhfb3RoZXJfbGVuZ3RoID0gbWF4KG1heF9vdGhlcl9sZW5ndGgsIHNuYWtlWyJsZW5ndGgiXSkKICAgICAgICAgICAgICAgIGZvciBzZWcgaW4gc25ha2VbImJvZHkiXToKICAgICAgICAgICAgICAgICAgICBhbGxfc25ha2VfYm9kaWVzLmFkZCh0dXBsZShzZWcudmFsdWVzKCkpKQoKICAgICAgICB0YWlsID0gdHVwbGUoeW91WyJib2R5Il1bLTFdLnZhbHVlcygpKQogICAgICAgIHlvdXJfYm9keV9zZXQgPSB7dHVwbGUoc2VnLnZhbHVlcygpKSBmb3Igc2VnIGluIHlvdVsiYm9keSJdWzotMV19CgogICAgICAgIHNob3VsZF9zZWVrX2Zvb2QgPSB5b3VyX2hlYWx0aCA8IDQwIG9yIHlvdXJfbGVuZ3RoIDw9IG1heF9vdGhlcl9sZW5ndGgKCiAgICAgICAgZGVmIGlzX3ZhbGlkKHgsIHkpOgogICAgICAgICAgICBpZiB4IDwgMCBvciB4ID49IHdpZHRoIG9yIHkgPCAwIG9yIHkgPj0gaGVpZ2h0OgogICAgICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAgICAgIGlmICh4LCB5KSBpbiBhbGxfc25ha2VfYm9kaWVzOgogICAgICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAgICAgIHJldHVybiBUcnVlCgogICAgICAgIGRlZiBpc19kZWFkX2VuZChwb3MsIGZvb2RfcG9zKToKICAgICAgICAgICAgcXVldWUgPSBkZXF1ZShbcG9zXSkKICAgICAgICAgICAgdmlzaXRlZCA9IHtwb3N9CiAgICAgICAgICAgIHBhdGhfZm91bmQgPSBwb3MgPT0gZm9vZF9wb3MKICAgICAgICAgICAgd2hpbGUgcXVldWUgYW5kIG5vdCBwYXRoX2ZvdW5kOgogICAgICAgICAgICAgICAgeCwgeSA9IHF1ZXVlLnBvcGxlZnQoKQogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgaXNfdmFsaWQobngsIG55KSBhbmQgKG54LCBueSkgbm90IGluIHZpc2l0ZWQ6CiAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgICAgICBpZiAobngsIG55KSA9PSBmb29kX3BvczoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHBhdGhfZm91bmQgPSBUcnVlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICAgICAgICAgICAgICBxdWV1ZS5hcHBlbmQoKG54LCBueSkpCiAgICAgICAgICAgIGlmIG5vdCBwYXRoX2ZvdW5kOgogICAgICAgICAgICAgICAgcmV0dXJuIFRydWUKICAgICAgICAgICAgd2FsbF9jb3VudCA9IHN1bSgxIGZvciBkeCwgZHkgaW4gWygwLCAxKSwgKDAsIC0xKSwgKDEsIDApLCAoLTEsIDApXSBpZiBub3QgaXNfdmFsaWQoZm9vZF9wb3NbMF0gKyBkeCwgZm9vZF9wb3NbMV0gKyBkeSkpCiAgICAgICAgICAgIHJldHVybiB3YWxsX2NvdW50ID49IDMKCiAgICAgICAgZGVmIGJmc19kaXN0YW5jZShzdGFydCwgdGFyZ2V0KToKICAgICAgICAgICAgcXVldWUgPSBkZXF1ZShbKHN0YXJ0LCAwKV0pCiAgICAgICAgICAgIHZpc2l0ZWQgPSB7c3RhcnR9CiAgICAgICAgICAgIHdoaWxlIHF1ZXVlOgogICAgICAgICAgICAgICAgcG9zLCBkaXN0ID0gcXVldWUucG9wbGVmdCgpCiAgICAgICAgICAgICAgICBpZiBwb3MgPT0gdGFyZ2V0OgogICAgICAgICAgICAgICAgICAgIHJldHVybiBkaXN0CiAgICAgICAgICAgICAgICB4LCB5ID0gcG9zCiAgICAgICAgICAgICAgICBmb3IgZHgsIGR5IGluIFsoMCwgMSksICgwLCAtMSksICgxLCAwKSwgKC0xLCAwKV06CiAgICAgICAgICAgICAgICAgICAgbngsIG55ID0geCArIGR4LCB5ICsgZHkKICAgICAgICAgICAgICAgICAgICBpZiBpc192YWxpZChueCwgbnkpIGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZDoKICAgICAgICAgICAgICAgICAgICAgICAgdmlzaXRlZC5hZGQoKG54LCBueSkpCiAgICAgICAgICAgICAgICAgICAgICAgIHF1ZXVlLmFwcGVuZCgoKG54LCBueSksIGRpc3QgKyAxKSkKICAgICAgICAgICAgcmV0dXJuIGZsb2F0KCdpbmYnKQoKICAgICAgICBuZWFyZXN0X2Zvb2QgPSBOb25lCiAgICAgICAgbWluX2Rpc3QgPSBmbG9hdCgnaW5mJykKICAgICAgICBmb3IgZiBpbiBmb29kX2xpc3Q6CiAgICAgICAgICAgIGlmIG5vdCBpc19kZWFkX2VuZCgoaGVhZFswXSwgaGVhZFsxXSksIGYpOgogICAgICAgICAgICAgICAgZCA9IGJmc19kaXN0YW5jZShoZWFkLCBmKQogICAgICAgICAgICAgICAgaWYgZCA8IG1pbl9kaXN0OgogICAgICAgICAgICAgICAgICAgIG1pbl9kaXN0ID0gZAogICAgICAgICAgICAgICAgICAgIG5lYXJlc3RfZm9vZCA9IGYKCiAgICAgICAgc2NvcmVzID0geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9CiAgICAgICAgbW92ZXMgPSB7InVwIjogKDAsIDEpLCAiZG93biI6ICgwLCAtMSksICJsZWZ0IjogKC0xLCAwKSwgInJpZ2h0IjogKDEsIDApfQoKICAgICAgICBmb3IgbW92ZV9uYW1lLCAoZHgsIGR5KSBpbiBtb3Zlcy5pdGVtcygpOgogICAgICAgICAgICBueCwgbnkgPSBoZWFkWzBdICsgZHgsIGhlYWRbMV0gKyBkeQoKICAgICAgICAgICAgaWYgbm90IGlzX3ZhbGlkKG54LCBueSk6CiAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV9uYW1lXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBpZiBzaG91bGRfc2Vla19mb29kIGFuZCBuZWFyZXN0X2Zvb2Q6CiAgICAgICAgICAgICAgICBtb3ZlX2Rpc3QgPSBiZnNfZGlzdGFuY2UoKG54LCBueSksIG5lYXJlc3RfZm9vZCkKICAgICAgICAgICAgICAgIGlmIG1vdmVfZGlzdCA8IG1pbl9kaXN0OgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gbWF4KDEwLjAsIDUuMCAtIG1vdmVfZGlzdCAqIDAuNSkKICAgICAgICAgICAgICAgIGVsaWYgbW92ZV9kaXN0ID09IG1pbl9kaXN0OgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gMi4wCiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlX25hbWVdID0gLTEuMAogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgc2NvcmVzW21vdmVfbmFtZV0gPSAwLjUKCiAgICAgICAgcmV0dXJuIHNjb3JlcwogICAgZXhjZXB0OgogICAgICAgIHJldHVybiB7bTogMC4wIGZvciBtIGluIFsidXAiLCAiZG93biIsICJsZWZ0IiwgInJpZ2h0Il19Cg=='}
_PRIORITY = ['space_control', 'combat', 'food']
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
