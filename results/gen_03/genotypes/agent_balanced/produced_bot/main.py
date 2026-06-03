# AUTO-ASSEMBLED decomposition bot (genotype balanced, gen 0).
# referee_policy=weighted_vote | specialists=['space_control', 'combat', 'food'] | tester=True | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'space_control': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHlvdSA9IGdhbWVfc3RhdGVbInlvdSJdCiAgICBib2FyZCA9IGdhbWVfc3RhdGVbImJvYXJkIl0KICAgIGhlYWQgPSB5b3VbImJvZHkiXVswXQogICAgdGFpbCA9IHlvdVsiYm9keSJdWy0xXQogICAgeW91cl9sZW5ndGggPSB5b3VbImxlbmd0aCJdCiAgICBoZWFkX3BvcyA9IChoZWFkWyJ4Il0sIGhlYWRbInkiXSkKICAgIHRhaWxfcG9zID0gKHRhaWxbIngiXSwgdGFpbFsieSJdKQogICAganVzdF9hdGUgPSBsZW4oeW91WyJib2R5Il0pID4gMSBhbmQgeW91WyJib2R5Il1bLTFdID09IHlvdVsiYm9keSJdWy0yXQogICAgb2NjdXBpZWQgPSBzZXQoKQogICAgZm9yIHNuYWtlIGluIGJvYXJkWyJzbmFrZXMiXToKICAgICAgICBmb3Igc2VnbWVudCBpbiBzbmFrZVsiYm9keSJdOgogICAgICAgICAgICBvY2N1cGllZC5hZGQoKHNlZ21lbnRbIngiXSwgc2VnbWVudFsieSJdKSkKICAgIGlmIG5vdCBqdXN0X2F0ZSBhbmQgdGFpbF9wb3MgaW4gb2NjdXBpZWQ6CiAgICAgICAgb2NjdXBpZWQuZGlzY2FyZCh0YWlsX3BvcykKCiAgICBkZWYgZmxvb2RfZmlsbChzdGFydF9wb3MpOgogICAgICAgIGlmIHN0YXJ0X3Bvc1swXSA8IDAgb3Igc3RhcnRfcG9zWzBdID49IGJvYXJkWyJ3aWR0aCJdIG9yIHN0YXJ0X3Bvc1sxXSA8IDAgb3Igc3RhcnRfcG9zWzFdID49IGJvYXJkWyJoZWlnaHQiXToKICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICBpZiBzdGFydF9wb3MgaW4gb2NjdXBpZWQ6CiAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAgdmlzaXRlZCA9IHtzdGFydF9wb3N9CiAgICAgICAgcSA9IGRlcXVlKFtzdGFydF9wb3NdKQogICAgICAgIHdoaWxlIHE6CiAgICAgICAgICAgIHgsIHkgPSBxLnBvcGxlZnQoKQogICAgICAgICAgICBmb3IgZHgsIGR5IGluIFsoMCwgMSksICgwLCAtMSksICgtMSwgMCksICgxLCAwKV06CiAgICAgICAgICAgICAgICBueCwgbnkgPSB4ICsgZHgsIHkgKyBkeQogICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IGJvYXJkWyJ3aWR0aCJdIGFuZCAwIDw9IG55IDwgYm9hcmRbImhlaWdodCJdIGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZCBhbmQgKG54LCBueSkgbm90IGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChueCwgbnkpKQogICAgICAgICAgICAgICAgICAgIHEuYXBwZW5kKChueCwgbnkpKQogICAgICAgIHJldHVybiBsZW4odmlzaXRlZCkKCiAgICBtb3ZlcyA9IHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQogICAgZGlyZWN0aW9ucyA9IHsidXAiOiAoMCwgMSksICJkb3duIjogKDAsIC0xKSwgImxlZnQiOiAoLTEsIDApLCAicmlnaHQiOiAoMSwgMCl9CiAgICBmb3IgbW92ZV9uYW1lLCAoZHgsIGR5KSBpbiBkaXJlY3Rpb25zLml0ZW1zKCk6CiAgICAgICAgbmV3X3gsIG5ld195ID0gaGVhZF9wb3NbMF0gKyBkeCwgaGVhZF9wb3NbMV0gKyBkeQogICAgICAgIG5ld19wb3MgPSAobmV3X3gsIG5ld195KQogICAgICAgIGlmIG5ld194IDwgMCBvciBuZXdfeCA+PSBib2FyZFsid2lkdGgiXSBvciBuZXdfeSA8IDAgb3IgbmV3X3kgPj0gYm9hcmRbImhlaWdodCJdOgogICAgICAgICAgICBtb3Zlc1ttb3ZlX25hbWVdID0gLTFlOQogICAgICAgICAgICBjb250aW51ZQogICAgICAgIGlmIG5ld19wb3MgaW4gb2NjdXBpZWQ6CiAgICAgICAgICAgIG1vdmVzW21vdmVfbmFtZV0gPSAtMWU5CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgYmxvY2tlZCA9IG9jY3VwaWVkIHwge25ld19wb3N9CiAgICAgICAgaWYgbm90IGp1c3RfYXRlOgogICAgICAgICAgICBibG9ja2VkLmRpc2NhcmQodGFpbF9wb3MpCiAgICAgICAgc3BhY2UgPSBmbG9vZF9maWxsKG5ld19wb3MpCiAgICAgICAgaWYgc3BhY2UgPCB5b3VyX2xlbmd0aDoKICAgICAgICAgICAgbW92ZXNbbW92ZV9uYW1lXSA9IC0xZTkKICAgICAgICBlbHNlOgogICAgICAgICAgICBtb3Zlc1ttb3ZlX25hbWVdID0gZmxvYXQoc3BhY2UpCiAgICByZXR1cm4gbW92ZXMK', 'combat': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpIC0+IGRpY3Q6CiAgICB0cnk6CiAgICAgICAgeW91ID0gZ2FtZV9zdGF0ZS5nZXQoInlvdSIsIHt9KQogICAgICAgIGJvYXJkID0gZ2FtZV9zdGF0ZS5nZXQoImJvYXJkIiwge30pCiAgICAgICAgeW91cl9oZWFkID0geW91LmdldCgiYm9keSIsIFt7fV0pWzBdCiAgICAgICAgeW91cl9sZW5ndGggPSB5b3UuZ2V0KCJsZW5ndGgiLCAwKQogICAgICAgIHlvdXJfaGVhbHRoID0geW91LmdldCgiaGVhbHRoIiwgMTAwKQoKICAgICAgICBpZiBub3QgeW91cl9oZWFkIG9yICJ4IiBub3QgaW4geW91cl9oZWFkIG9yICJ5IiBub3QgaW4geW91cl9oZWFkOgogICAgICAgICAgICByZXR1cm4ge206IDAuMCBmb3IgbSBpbiBbInVwIiwgImRvd24iLCAibGVmdCIsICJyaWdodCJdfQoKICAgICAgICB3aWR0aCA9IGJvYXJkLmdldCgid2lkdGgiLCAxMSkKICAgICAgICBoZWlnaHQgPSBib2FyZC5nZXQoImhlaWdodCIsIDExKQogICAgICAgIHNuYWtlcyA9IGJvYXJkLmdldCgic25ha2VzIiwgW10pCiAgICAgICAgeW91cl9ib2R5X3NldCA9IHNldCgoc2VnWyJ4Il0sIHNlZ1sieSJdKSBmb3Igc2VnIGluIHlvdS5nZXQoImJvZHkiLCBbXSkpCiAgICAgICAgeW91cl90YWlsID0gKHlvdS5nZXQoImJvZHkiLCBbe31dKVstMV0uZ2V0KCJ4IiksIHlvdS5nZXQoImJvZHkiLCBbe31dKVstMV0uZ2V0KCJ5IikpCiAgICAgICAganVzdF9hdGUgPSBsZW4oeW91LmdldCgiYm9keSIsIFtdKSkgPj0gMiBhbmQgeW91LmdldCgiYm9keSIsIFtdKVstMV0gPT0geW91LmdldCgiYm9keSIsIFtdKVstMl0KCiAgICAgICAgbW92ZXMgPSB7CiAgICAgICAgICAgICJ1cCI6ICh5b3VyX2hlYWRbIngiXSwgeW91cl9oZWFkWyJ5Il0gKyAxKSwKICAgICAgICAgICAgImRvd24iOiAoeW91cl9oZWFkWyJ4Il0sIHlvdXJfaGVhZFsieSJdIC0gMSksCiAgICAgICAgICAgICJsZWZ0IjogKHlvdXJfaGVhZFsieCJdIC0gMSwgeW91cl9oZWFkWyJ5Il0pLAogICAgICAgICAgICAicmlnaHQiOiAoeW91cl9oZWFkWyJ4Il0gKyAxLCB5b3VyX2hlYWRbInkiXSkKICAgICAgICB9CgogICAgICAgIHNjb3JlcyA9IHt9CiAgICAgICAgZm9yIGRpcmVjdGlvbiwgKG54LCBueSkgaW4gbW92ZXMuaXRlbXMoKToKICAgICAgICAgICAgaWYgbnggPCAwIG9yIG54ID49IHdpZHRoIG9yIG55IDwgMCBvciBueSA+PSBoZWlnaHQ6CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBjZWxsID0gKG54LCBueSkKICAgICAgICAgICAgZm9yYmlkZGVuID0geW91cl9ib2R5X3NldCAtIHt5b3VyX3RhaWx9IGlmIG5vdCBqdXN0X2F0ZSBlbHNlIHlvdXJfYm9keV9zZXQKICAgICAgICAgICAgaWYgY2VsbCBpbiBmb3JiaWRkZW46CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBsb3NlX2NvbGxpc2lvbiA9IEZhbHNlCiAgICAgICAgICAgIHdpbl9jb2xsaXNpb24gPSBGYWxzZQogICAgICAgICAgICBlbmVteV9ib2R5X3RocmVhdCA9IEZhbHNlCiAgICAgICAgICAgIHRocmVhdF9jb3VudCA9IDAKCiAgICAgICAgICAgIGZvciBlbmVteSBpbiBzbmFrZXM6CiAgICAgICAgICAgICAgICBpZiBlbmVteS5nZXQoImlkIikgPT0geW91LmdldCgiaWQiKToKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgZW5lbXlfaGVhZCA9IGVuZW15LmdldCgiYm9keSIsIFt7fV0pWzBdCiAgICAgICAgICAgICAgICBlbmVteV9sZW5ndGggPSBlbmVteS5nZXQoImxlbmd0aCIsIDApCiAgICAgICAgICAgICAgICBlbmVteV9ib2R5ID0gc2V0KChzZWdbIngiXSwgc2VnWyJ5Il0pIGZvciBzZWcgaW4gZW5lbXkuZ2V0KCJib2R5IiwgW10pKQoKICAgICAgICAgICAgICAgIGlmIG5vdCBlbmVteV9oZWFkIG9yICJ4IiBub3QgaW4gZW5lbXlfaGVhZCBvciAieSIgbm90IGluIGVuZW15X2hlYWQ6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICAgICBpZiBjZWxsIGluIGVuZW15X2JvZHk6CiAgICAgICAgICAgICAgICAgICAgZW5lbXlfYm9keV90aHJlYXQgPSBUcnVlCiAgICAgICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICAgICBlbmVteV9tb3ZlcyA9IFsKICAgICAgICAgICAgICAgICAgICAoZW5lbXlfaGVhZFsieCJdLCBlbmVteV9oZWFkWyJ5Il0gKyAxKSwKICAgICAgICAgICAgICAgICAgICAoZW5lbXlfaGVhZFsieCJdLCBlbmVteV9oZWFkWyJ5Il0gLSAxKSwKICAgICAgICAgICAgICAgICAgICAoZW5lbXlfaGVhZFsieCJdIC0gMSwgZW5lbXlfaGVhZFsieSJdKSwKICAgICAgICAgICAgICAgICAgICAoZW5lbXlfaGVhZFsieCJdICsgMSwgZW5lbXlfaGVhZFsieSJdKQogICAgICAgICAgICAgICAgXQoKICAgICAgICAgICAgICAgIGlmIGNlbGwgaW4gZW5lbXlfbW92ZXM6CiAgICAgICAgICAgICAgICAgICAgaWYgZW5lbXlfbGVuZ3RoID49IHlvdXJfbGVuZ3RoOgogICAgICAgICAgICAgICAgICAgICAgICBsb3NlX2NvbGxpc2lvbiA9IFRydWUKICAgICAgICAgICAgICAgICAgICBlbGlmIGVuZW15X2xlbmd0aCA8IHlvdXJfbGVuZ3RoOgogICAgICAgICAgICAgICAgICAgICAgICB3aW5fY29sbGlzaW9uID0gVHJ1ZQogICAgICAgICAgICAgICAgICAgICAgICB0aHJlYXRfY291bnQgKz0gMQoKICAgICAgICAgICAgaWYgZW5lbXlfYm9keV90aHJlYXQgb3IgbG9zZV9jb2xsaXNpb246CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgZWxpZiB3aW5fY29sbGlzaW9uOgogICAgICAgICAgICAgICAgc2NvcmVzW2RpcmVjdGlvbl0gPSAxMC4wICsgdGhyZWF0X2NvdW50CiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IDAuMAoKICAgICAgICByZXR1cm4gc2NvcmVzCiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHttOiAwLjAgZm9yIG0gaW4gWyJ1cCIsICJkb3duIiwgImxlZnQiLCAicmlnaHQiXX0K', 'food': 'ZnJvbSBjb2xsZWN0aW9ucyBpbXBvcnQgZGVxdWUKCmRlZiBzY29yZShnYW1lX3N0YXRlKToKICAgIHRyeToKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlWyJ5b3UiXQogICAgICAgIGJvYXJkID0gZ2FtZV9zdGF0ZVsiYm9hcmQiXQogICAgICAgIGhlYWQgPSB0dXBsZSgoeW91WyJib2R5Il1bMF1bIngiXSwgeW91WyJib2R5Il1bMF1bInkiXSkpCiAgICAgICAgaGVhbHRoID0geW91WyJoZWFsdGgiXQogICAgICAgIGxlbmd0aCA9IHlvdVsibGVuZ3RoIl0KICAgICAgICB3aWR0aCwgaGVpZ2h0ID0gYm9hcmRbIndpZHRoIl0sIGJvYXJkWyJoZWlnaHQiXQoKICAgICAgICBhbGxfYm9kaWVzID0gc2V0KCkKICAgICAgICBmb3Igc25ha2UgaW4gYm9hcmRbInNuYWtlcyJdOgogICAgICAgICAgICBmb3IgY2VsbCBpbiBzbmFrZVsiYm9keSJdOgogICAgICAgICAgICAgICAgYWxsX2JvZGllcy5hZGQodHVwbGUoKGNlbGxbIngiXSwgY2VsbFsieSJdKSkpCgogICAgICAgIHRhaWwgPSB0dXBsZSgoeW91WyJib2R5Il1bLTFdWyJ4Il0sIHlvdVsiYm9keSJdWy0xXVsieSJdKSkKICAgICAgICB0YWlsX2ZyZWUgPSBsZW4oeW91WyJib2R5Il0pID4gMSBhbmQgeW91WyJib2R5Il1bLTFdICE9IHlvdVsiYm9keSJdWy0yXQoKICAgICAgICBib2R5X3NldCA9IHNldCgoc2VnWyJ4Il0sIHNlZ1sieSJdKSBmb3Igc2VnIGluIHlvdVsiYm9keSJdKQogICAgICAgIGlmIHRhaWxfZnJlZToKICAgICAgICAgICAgYm9keV9zZXQuZGlzY2FyZCh0YWlsKQoKICAgICAgICBmb29kX2xpc3QgPSBbdHVwbGUoKGZbIngiXSwgZlsieSJdKSkgZm9yIGYgaW4gYm9hcmRbImZvb2QiXV0KICAgICAgICBpZiBub3QgZm9vZF9saXN0OgogICAgICAgICAgICByZXR1cm4ge206IDAuMCBmb3IgbSBpbiBbInVwIiwgImRvd24iLCAibGVmdCIsICJyaWdodCJdfQoKICAgICAgICBtYXhfZW5lbXlfbGVuID0gbWF4KChzWyJsZW5ndGgiXSBmb3IgcyBpbiBib2FyZFsic25ha2VzIl0gaWYgc1siaWQiXSAhPSB5b3VbImlkIl0pLCBkZWZhdWx0PTApCiAgICAgICAgc2Vla19mb29kID0gaGVhbHRoIDw9IDQwIG9yIGxlbmd0aCA8IG1heF9lbmVteV9sZW4KCiAgICAgICAgbmVhcmVzdF9mb29kID0gbWluKGZvb2RfbGlzdCwga2V5PWxhbWJkYSBmOiBhYnMoZlswXSAtIGhlYWRbMF0pICsgYWJzKGZbMV0gLSBoZWFkWzFdKSkKCiAgICAgICAgZGVmIGlzX2RlYWRfZW5kKHBvcyk6CiAgICAgICAgICAgIHZpc2l0ZWQgPSB7cG9zfQogICAgICAgICAgICBxID0gZGVxdWUoW3Bvc10pCiAgICAgICAgICAgIGV4aXRfY291bnQgPSAwCiAgICAgICAgICAgIHdoaWxlIHE6CiAgICAgICAgICAgICAgICBjdXJyID0gcS5wb3BsZWZ0KCkKICAgICAgICAgICAgICAgIGN4LCBjeSA9IGN1cnIKICAgICAgICAgICAgICAgIGZvciBkeCwgZHkgaW4gWygwLCAxKSwgKDAsIC0xKSwgKC0xLCAwKSwgKDEsIDApXToKICAgICAgICAgICAgICAgICAgICBueCwgbnkgPSBjeCArIGR4LCBjeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgbm90ICgwIDw9IG54IDwgd2lkdGggYW5kIDAgPD0gbnkgPCBoZWlnaHQpOgogICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgIG5wb3MgPSAobngsIG55KQogICAgICAgICAgICAgICAgICAgIGlmIG5wb3Mgbm90IGluIHZpc2l0ZWQgYW5kIG5wb3Mgbm90IGluIGFsbF9ib2RpZXM6CiAgICAgICAgICAgICAgICAgICAgICAgIHZpc2l0ZWQuYWRkKG5wb3MpCiAgICAgICAgICAgICAgICAgICAgICAgIHEuYXBwZW5kKG5wb3MpCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIGxlbih2aXNpdGVkKSA+IGxlbmd0aDoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBGYWxzZQogICAgICAgICAgICByZXR1cm4gbGVuKHZpc2l0ZWQpIDw9IGxlbmd0aAoKICAgICAgICBzY29yZXMgPSB7fQogICAgICAgIGZvciBtb3ZlLCAoZHgsIGR5KSBpbiBbKCJ1cCIsICgwLCAxKSksICgiZG93biIsICgwLCAtMSkpLCAoImxlZnQiLCAoLTEsIDApKSwgKCJyaWdodCIsICgxLCAwKSldOgogICAgICAgICAgICBueCwgbnkgPSBoZWFkWzBdICsgZHgsIGhlYWRbMV0gKyBkeQoKICAgICAgICAgICAgaWYgbm90ICgwIDw9IG54IDwgd2lkdGggYW5kIDAgPD0gbnkgPCBoZWlnaHQpOgogICAgICAgICAgICAgICAgc2NvcmVzW21vdmVdID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIG5leHRfY2VsbCA9IChueCwgbnkpCiAgICAgICAgICAgIGlmIG5leHRfY2VsbCBpbiBhbGxfYm9kaWVzIGFuZCBuZXh0X2NlbGwgIT0gdGFpbDoKICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBpZiBub3Qgc2Vla19mb29kOgogICAgICAgICAgICAgICAgc2NvcmVzW21vdmVdID0gMC4wCiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICBpZiBuZXh0X2NlbGwgPT0gbmVhcmVzdF9mb29kIGFuZCBpc19kZWFkX2VuZChuZWFyZXN0X2Zvb2QpOgogICAgICAgICAgICAgICAgICAgIHNjb3Jlc1ttb3ZlXSA9IC0xZTkKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgICAgIGN1cnJfZGlzdCA9IGFicyhoZWFkWzBdIC0gbmVhcmVzdF9mb29kWzBdKSArIGFicyhoZWFkWzFdIC0gbmVhcmVzdF9mb29kWzFdKQogICAgICAgICAgICAgICAgbmV4dF9kaXN0ID0gYWJzKG54IC0gbmVhcmVzdF9mb29kWzBdKSArIGFicyhueSAtIG5lYXJlc3RfZm9vZFsxXSkKICAgICAgICAgICAgICAgIHByb2dyZXNzID0gY3Vycl9kaXN0IC0gbmV4dF9kaXN0CgogICAgICAgICAgICAgICAgaWYgbmV4dF9jZWxsID09IG5lYXJlc3RfZm9vZDoKICAgICAgICAgICAgICAgICAgICBzY29yZXNbbW92ZV0gPSAxMC4wICsgcHJvZ3Jlc3MKICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgc2NvcmVzW21vdmVdID0gZmxvYXQocHJvZ3Jlc3MpIGlmIHByb2dyZXNzID4gMCBlbHNlIDAuMAoKICAgICAgICByZXR1cm4gc2NvcmVzCiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHsidXAiOiAwLjAsICJkb3duIjogMC4wLCAibGVmdCI6IDAuMCwgInJpZ2h0IjogMC4wfQo='}
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
