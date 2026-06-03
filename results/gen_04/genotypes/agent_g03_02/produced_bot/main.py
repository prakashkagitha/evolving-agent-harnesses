# AUTO-ASSEMBLED decomposition bot (genotype g03_02, gen 3).
# referee_policy=weighted_vote | specialists=['space_control', 'food', 'combat'] | tester=True | refine_rounds=2
# Each specialist is exec'd in its own namespace (base64) so helpers never collide.
import base64
import typing

_SPEC_B64 = {'space_control': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgIiIiU3BhY2UgY29udHJvbCBzcGVjaWFsaXN0OiBtYXhpbWl6ZSByZWFjaGFibGUgb3BlbiBhcmVhIHZpYSBmbG9vZC1maWxsLiIiIgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGUuZ2V0KCJ5b3UiLCB7fSkKICAgICAgICBib2FyZCA9IGdhbWVfc3RhdGUuZ2V0KCJib2FyZCIsIHt9KQoKICAgICAgICBpZiBub3QgeW91IG9yIG5vdCBib2FyZDoKICAgICAgICAgICAgcmV0dXJuIHttOiAwLjAgZm9yIG0gaW4gWyJ1cCIsICJkb3duIiwgImxlZnQiLCAicmlnaHQiXX0KCiAgICAgICAgaGVhZCA9IHlvdVsiYm9keSJdWzBdCiAgICAgICAgeW91cl9sZW5ndGggPSB5b3VbImxlbmd0aCJdCiAgICAgICAganVzdF9hdGUgPSBsZW4oeW91WyJib2R5Il0pID4gMSBhbmQgeW91WyJib2R5Il1bLTFdID09IHlvdVsiYm9keSJdWy0yXSBpZiB5b3VbImJvZHkiXSBlbHNlIEZhbHNlCgogICAgICAgIHdpZHRoID0gYm9hcmQuZ2V0KCJ3aWR0aCIsIDExKQogICAgICAgIGhlaWdodCA9IGJvYXJkLmdldCgiaGVpZ2h0IiwgMTEpCgogICAgICAgICMgQnVpbGQgc2V0IG9mIG9jY3VwaWVkIGNlbGxzIChhbGwgc25ha2UgYm9kaWVzLCBleGNsdWRpbmcgdGFpbHMgdGhhdCB3aWxsIG1vdmUpCiAgICAgICAgb2NjdXBpZWQgPSBzZXQoKQogICAgICAgIGFsbF9zbmFrZV9ib2RpZXMgPSB7fQogICAgICAgIGZvciBzbmFrZSBpbiBib2FyZC5nZXQoInNuYWtlcyIsIFtdKToKICAgICAgICAgICAgYm9keSA9IHNuYWtlLmdldCgiYm9keSIsIFtdKQogICAgICAgICAgICBhbGxfc25ha2VfYm9kaWVzW3NuYWtlWyJpZCJdXSA9IGJvZHkKICAgICAgICAgICAgZm9yIGksIHNlZ21lbnQgaW4gZW51bWVyYXRlKGJvZHkpOgogICAgICAgICAgICAgICAgY2VsbCA9IChzZWdtZW50WyJ4Il0sIHNlZ21lbnRbInkiXSkKICAgICAgICAgICAgICAgICMgRXhjbHVkZSB0YWlsIG9mIG90aGVyIHNuYWtlcyAodGhleSB3aWxsIG1vdmUgYXdheSkKICAgICAgICAgICAgICAgIGlmIHNuYWtlWyJpZCJdID09IHlvdVsiaWQiXToKICAgICAgICAgICAgICAgICAgICAjIEZvciB5b3VyIHNuYWtlOiBleGNsdWRlIHRhaWwgb25seSBpZiB5b3UgZGlkbid0IGp1c3QgZWF0CiAgICAgICAgICAgICAgICAgICAgaWYgaSA8IGxlbihib2R5KSAtIDEgb3IganVzdF9hdGU6CiAgICAgICAgICAgICAgICAgICAgICAgIG9jY3VwaWVkLmFkZChjZWxsKQogICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAjIE90aGVyIHNuYWtlczogYWx3YXlzIGV4Y2x1ZGUgdGhlaXIgdGFpbCAoaXQgbW92ZXMgYXdheSBuZXh0IHR1cm4pCiAgICAgICAgICAgICAgICAgICAgaWYgaSA8IGxlbihib2R5KSAtIDE6CiAgICAgICAgICAgICAgICAgICAgICAgIG9jY3VwaWVkLmFkZChjZWxsKQoKICAgICAgICAjIEhhemFyZCBjZWxscwogICAgICAgIGhhemFyZHMgPSBzZXQoKGhbIngiXSwgaFsieSJdKSBmb3IgaCBpbiBib2FyZC5nZXQoImhhemFyZHMiLCBbXSkpCgogICAgICAgIGRlZiBmbG9vZF9maWxsKHN0YXJ0X3gsIHN0YXJ0X3kpOgogICAgICAgICAgICAiIiJDb3VudCByZWFjaGFibGUgY2VsbHMgZnJvbSBzdGFydCBwb3NpdGlvbiB2aWEgQkZTLiIiIgogICAgICAgICAgICBpZiBub3QgKDAgPD0gc3RhcnRfeCA8IHdpZHRoIGFuZCAwIDw9IHN0YXJ0X3kgPCBoZWlnaHQpOgogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgaWYgKHN0YXJ0X3gsIHN0YXJ0X3kpIGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgcmV0dXJuIDAKCiAgICAgICAgICAgIHZpc2l0ZWQgPSBzZXQoKQogICAgICAgICAgICBxdWV1ZSA9IFsoc3RhcnRfeCwgc3RhcnRfeSldCiAgICAgICAgICAgIHZpc2l0ZWQuYWRkKChzdGFydF94LCBzdGFydF95KSkKCiAgICAgICAgICAgIHdoaWxlIHF1ZXVlOgogICAgICAgICAgICAgICAgeCwgeSA9IHF1ZXVlLnBvcCgwKQogICAgICAgICAgICAgICAgZm9yIGR4LCBkeSBpbiBbKDAsIDEpLCAoMCwgLTEpLCAoMSwgMCksICgtMSwgMCldOgogICAgICAgICAgICAgICAgICAgIG54LCBueSA9IHggKyBkeCwgeSArIGR5CiAgICAgICAgICAgICAgICAgICAgaWYgMCA8PSBueCA8IHdpZHRoIGFuZCAwIDw9IG55IDwgaGVpZ2h0IGFuZCAobngsIG55KSBub3QgaW4gdmlzaXRlZCBhbmQgKG54LCBueSkgbm90IGluIG9jY3VwaWVkOgogICAgICAgICAgICAgICAgICAgICAgICB2aXNpdGVkLmFkZCgobngsIG55KSkKICAgICAgICAgICAgICAgICAgICAgICAgcXVldWUuYXBwZW5kKChueCwgbnkpKQoKICAgICAgICAgICAgcmV0dXJuIGxlbih2aXNpdGVkKQoKICAgICAgICBtb3ZlcyA9IHsKICAgICAgICAgICAgInVwIjogKGhlYWRbIngiXSwgaGVhZFsieSJdICsgMSksCiAgICAgICAgICAgICJkb3duIjogKGhlYWRbIngiXSwgaGVhZFsieSJdIC0gMSksCiAgICAgICAgICAgICJsZWZ0IjogKGhlYWRbIngiXSAtIDEsIGhlYWRbInkiXSksCiAgICAgICAgICAgICJyaWdodCI6IChoZWFkWyJ4Il0gKyAxLCBoZWFkWyJ5Il0pLAogICAgICAgIH0KCiAgICAgICAgcmVzdWx0ID0ge30KICAgICAgICBmb3IgZGlyZWN0aW9uLCAobmV4dF94LCBuZXh0X3kpIGluIG1vdmVzLml0ZW1zKCk6CiAgICAgICAgICAgICMgSGFyZCB2ZXRvOiB3YWxsCiAgICAgICAgICAgIGlmIG5vdCAoMCA8PSBuZXh0X3ggPCB3aWR0aCBhbmQgMCA8PSBuZXh0X3kgPCBoZWlnaHQpOgogICAgICAgICAgICAgICAgcmVzdWx0W2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgIyBIYXJkIHZldG86IHNuYWtlIGJvZHkgKGluY2x1ZGluZyBvdGhlciBoZWFkcykKICAgICAgICAgICAgaWYgKG5leHRfeCwgbmV4dF95KSBpbiBvY2N1cGllZDoKICAgICAgICAgICAgICAgIHJlc3VsdFtkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICMgSGFyZCB2ZXRvOiBtb3ZpbmcgaW50byBoYXphcmQKICAgICAgICAgICAgaWYgKG5leHRfeCwgbmV4dF95KSBpbiBoYXphcmRzOgogICAgICAgICAgICAgICAgcmVzdWx0W2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgIyBDb25zZXJ2YXRpdmU6IHBlbmFsaXplIG1vdmluZyBhZGphY2VudCB0byBlbmVteSBoZWFkcyAodGhleSBjYW4gYXR0YWNrIG5leHQgdHVybikKICAgICAgICAgICAgcGVuYWx0eSA9IDAuMAogICAgICAgICAgICBmb3Igc25ha2UgaW4gYm9hcmQuZ2V0KCJzbmFrZXMiLCBbXSk6CiAgICAgICAgICAgICAgICBpZiBzbmFrZVsiaWQiXSAhPSB5b3VbImlkIl06CiAgICAgICAgICAgICAgICAgICAgZW5lbXlfaGVhZCA9IHNuYWtlWyJib2R5Il1bMF0KICAgICAgICAgICAgICAgICAgICBlbmVteV9wb3MgPSAoZW5lbXlfaGVhZFsieCJdLCBlbmVteV9oZWFkWyJ5Il0pCiAgICAgICAgICAgICAgICAgICAgZW5lbXlfbGVuZ3RoID0gc25ha2VbImxlbmd0aCJdCiAgICAgICAgICAgICAgICAgICAgIyBJZiBlbmVteSBpcyBsb25nZXIgYW5kIGFkamFjZW50LCBoZWF2aWx5IHBlbmFsaXplCiAgICAgICAgICAgICAgICAgICAgaWYgYWJzKGVuZW15X3Bvc1swXSAtIG5leHRfeCkgKyBhYnMoZW5lbXlfcG9zWzFdIC0gbmV4dF95KSA9PSAxOgogICAgICAgICAgICAgICAgICAgICAgICBpZiBlbmVteV9sZW5ndGggPj0geW91cl9sZW5ndGg6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwZW5hbHR5ID0gLTUwMC4wCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVhawoKICAgICAgICAgICAgaWYgcGVuYWx0eSA8IC0xMDA6CiAgICAgICAgICAgICAgICByZXN1bHRbZGlyZWN0aW9uXSA9IHBlbmFsdHkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICAjIENhbGN1bGF0ZSByZWFjaGFibGUgc3BhY2UgZnJvbSB0aGlzIG1vdmUKICAgICAgICAgICAgcmVhY2hhYmxlID0gZmxvb2RfZmlsbChuZXh0X3gsIG5leHRfeSkKCiAgICAgICAgICAgICMgSGFyZCB2ZXRvOiBwb2NrZXQgc21hbGxlciB0aGFuIHlvdXIgbGVuZ3RoIChzZWxmLXRyYXApCiAgICAgICAgICAgIGlmIHJlYWNoYWJsZSA8IHlvdXJfbGVuZ3RoOgogICAgICAgICAgICAgICAgcmVzdWx0W2RpcmVjdGlvbl0gPSAtMWU5CiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgIyBTY29yZTogbnVtYmVyIG9mIHJlYWNoYWJsZSBjZWxscyAoaGlnaGVyIGlzIGJldHRlcikgcGx1cyBwZW5hbHR5CiAgICAgICAgICAgIHJlc3VsdFtkaXJlY3Rpb25dID0gZmxvYXQocmVhY2hhYmxlKSArIHBlbmFsdHkKCiAgICAgICAgcmV0dXJuIHJlc3VsdAogICAgZXhjZXB0OgogICAgICAgIHJldHVybiB7bTogMC4wIGZvciBtIGluIFsidXAiLCAiZG93biIsICJsZWZ0IiwgInJpZ2h0Il19Cg==', 'food': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpIC0+IGRpY3Q6CiAgICB0cnk6CiAgICAgICAgYm9hcmQgPSBnYW1lX3N0YXRlLmdldCgiYm9hcmQiLCB7fSkKICAgICAgICB5b3UgPSBnYW1lX3N0YXRlLmdldCgieW91Iiwge30pCiAgICAgICAgeW91cl9oZWFkID0gdHVwbGUoeW91WyJib2R5Il1bMF0udmFsdWVzKCkpCiAgICAgICAgeW91cl9sZW5ndGggPSB5b3UuZ2V0KCJsZW5ndGgiLCAxKQogICAgICAgIHlvdXJfaGVhbHRoID0geW91LmdldCgiaGVhbHRoIiwgMTAwKQogICAgICAgIHdpZHRoLCBoZWlnaHQgPSBib2FyZC5nZXQoIndpZHRoIiwgMTEpLCBib2FyZC5nZXQoImhlaWdodCIsIDExKQogICAgICAgIGZvb2QgPSBbdHVwbGUoZi52YWx1ZXMoKSkgZm9yIGYgaW4gYm9hcmQuZ2V0KCJmb29kIiwgW10pXQogICAgICAgIHNuYWtlcyA9IGJvYXJkLmdldCgic25ha2VzIiwgW10pCiAgICAgICAgbWF4X2VuZW15X2xlbmd0aCA9IG1heChbc1sibGVuZ3RoIl0gZm9yIHMgaW4gc25ha2VzIGlmIHNbImlkIl0gIT0geW91WyJpZCJdXSwgZGVmYXVsdD0wKQogICAgICAgIGlzX2JlaGluZCA9IHlvdXJfbGVuZ3RoIDw9IG1heF9lbmVteV9sZW5ndGgKICAgICAgICBzaG91bGRfZWF0ID0geW91cl9oZWFsdGggPCA0MCBvciBpc19iZWhpbmQKICAgICAgICB2ZXRvID0gLTFlOQogICAgICAgIG1vdmVzID0geyJ1cCI6IDAuMCwgImRvd24iOiAwLjAsICJsZWZ0IjogMC4wLCAicmlnaHQiOiAwLjB9CiAgICAgICAgZGVsdGFzID0geyJ1cCI6ICgwLCAxKSwgImRvd24iOiAoMCwgLTEpLCAibGVmdCI6ICgtMSwgMCksICJyaWdodCI6ICgxLCAwKX0KCiAgICAgICAgZm9yIGRpcmVjdGlvbiwgKGR4LCBkeSkgaW4gZGVsdGFzLml0ZW1zKCk6CiAgICAgICAgICAgIG54LCBueSA9IHlvdXJfaGVhZFswXSArIGR4LCB5b3VyX2hlYWRbMV0gKyBkeQogICAgICAgICAgICBpZiBueCA8IDAgb3IgbnggPj0gd2lkdGggb3IgbnkgPCAwIG9yIG55ID49IGhlaWdodDoKICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSB2ZXRvCiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBuZXh0X3BvcyA9IChueCwgbnkpCiAgICAgICAgICAgIGlmIGFueShuZXh0X3BvcyA9PSB0dXBsZShzZWcudmFsdWVzKCkpIGZvciBzIGluIHNuYWtlcyBpZiBzWyJpZCJdICE9IHlvdVsiaWQiXSBmb3Igc2VnIGluIHNbImJvZHkiXVs6LTFdKToKICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSB2ZXRvCiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBpZiBzaG91bGRfZWF0OgogICAgICAgICAgICAgICAgbmVhcmVzdF9kaXN0ID0gZmxvYXQoImluZiIpCiAgICAgICAgICAgICAgICBpbl9kZWFkX2VuZCA9IEZhbHNlCiAgICAgICAgICAgICAgICBmb3IgZiBpbiBmb29kOgogICAgICAgICAgICAgICAgICAgIGRpc3QgPSBhYnMoZlswXSAtIG54KSArIGFicyhmWzFdIC0gbnkpCiAgICAgICAgICAgICAgICAgICAgaWYgZGlzdCA8IG5lYXJlc3RfZGlzdDoKICAgICAgICAgICAgICAgICAgICAgICAgbmVhcmVzdF9kaXN0ID0gZGlzdAogICAgICAgICAgICAgICAgICAgICAgICBpZiBuZXh0X3BvcyA9PSBmOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgcmVhY2hhYmxlID0gc2V0KCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN0YWNrID0gW2ZdCiAgICAgICAgICAgICAgICAgICAgICAgICAgICB2aXNpdGVkID0ge2Z9CiAgICAgICAgICAgICAgICAgICAgICAgICAgICB3aGlsZSBzdGFjazoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBjeCwgY3kgPSBzdGFjay5wb3AoKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJlYWNoYWJsZS5hZGQoKGN4LCBjeSkpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9yIG5keCwgbmR5IGluIFsoMCwgMSksICgwLCAtMSksICgtMSwgMCksICgxLCAwKV06CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG5jLCBuciA9IGN4ICsgbmR4LCBjeSArIG5keQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiAwIDw9IG5jIDwgd2lkdGggYW5kIDAgPD0gbnIgPCBoZWlnaHQgYW5kIChuYywgbnIpIG5vdCBpbiB2aXNpdGVkIGFuZCBub3QgYW55KChuYywgbnIpID09IHR1cGxlKHNlZy52YWx1ZXMoKSkgZm9yIHMgaW4gc25ha2VzIGlmIHNbImlkIl0gIT0geW91WyJpZCJdIGZvciBzZWcgaW4gc1siYm9keSJdWzotMV0pOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdmlzaXRlZC5hZGQoKG5jLCBucikpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdGFjay5hcHBlbmQoKG5jLCBucikpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBsZW4ocmVhY2hhYmxlKSA8IHlvdXJfbGVuZ3RoOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGluX2RlYWRfZW5kID0gVHJ1ZQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgICAgICBpZiBpbl9kZWFkX2VuZCBvciBuZWFyZXN0X2Rpc3QgPT0gZmxvYXQoImluZiIpOgogICAgICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSB2ZXRvCiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSBtYXgoMC4wLCAxMC4wIC0gbmVhcmVzdF9kaXN0ICogMC41KQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgbmVhcmVzdF9kaXN0ID0gZmxvYXQoImluZiIpCiAgICAgICAgICAgICAgICBmb3IgZiBpbiBmb29kOgogICAgICAgICAgICAgICAgICAgIGRpc3QgPSBhYnMoZlswXSAtIG54KSArIGFicyhmWzFdIC0gbnkpCiAgICAgICAgICAgICAgICAgICAgaWYgZGlzdCA8IG5lYXJlc3RfZGlzdDoKICAgICAgICAgICAgICAgICAgICAgICAgbmVhcmVzdF9kaXN0ID0gZGlzdAogICAgICAgICAgICAgICAgaWYgbmVhcmVzdF9kaXN0ID09IGZsb2F0KCJpbmYiKToKICAgICAgICAgICAgICAgICAgICBtb3Zlc1tkaXJlY3Rpb25dID0gMC4wCiAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgIG1vdmVzW2RpcmVjdGlvbl0gPSAtMC41ICsgKDEwLjAgLSBuZWFyZXN0X2Rpc3QgKiAwLjEpCiAgICAgICAgcmV0dXJuIG1vdmVzCiAgICBleGNlcHQ6CiAgICAgICAgcmV0dXJuIHttOiAwLjAgZm9yIG0gaW4gWyJ1cCIsICJkb3duIiwgImxlZnQiLCAicmlnaHQiXX0K', 'combat': 'ZGVmIHNjb3JlKGdhbWVfc3RhdGUpOgogICAgdHJ5OgogICAgICAgIHlvdSA9IGdhbWVfc3RhdGUuZ2V0KCJ5b3UiLCB7fSkKICAgICAgICBib2FyZCA9IGdhbWVfc3RhdGUuZ2V0KCJib2FyZCIsIHt9KQogICAgICAgIHlvdXJfaGVhZCA9IHR1cGxlKCh5b3UuZ2V0KCJib2R5IiwgW3t9XSlbMF0uZ2V0KCJ4IiksIHlvdS5nZXQoImJvZHkiLCBbe31dKVswXS5nZXQoInkiKSkpCiAgICAgICAgeW91cl9sZW5ndGggPSB5b3UuZ2V0KCJsZW5ndGgiLCAwKQogICAgICAgIHlvdXJfYm9keV9zZXQgPSB7KHNlZ1sieCJdLCBzZWdbInkiXSkgZm9yIHNlZyBpbiB5b3UuZ2V0KCJib2R5IiwgW10pfQoKICAgICAgICBzbmFrZXMgPSBib2FyZC5nZXQoInNuYWtlcyIsIFtdKQogICAgICAgIGVuZW15X2hlYWRzID0gW10KICAgICAgICBmb3Igc25ha2UgaW4gc25ha2VzOgogICAgICAgICAgICBpZiBzbmFrZS5nZXQoImlkIikgIT0geW91LmdldCgiaWQiKToKICAgICAgICAgICAgICAgIGhlYWQgPSBzbmFrZS5nZXQoImJvZHkiLCBbe31dKVswXQogICAgICAgICAgICAgICAgZW5lbXlfaGVhZHMuYXBwZW5kKHsicG9zIjogKGhlYWQuZ2V0KCJ4IiksIGhlYWQuZ2V0KCJ5IikpLCAibGVuZ3RoIjogc25ha2UuZ2V0KCJsZW5ndGgiLCAwKX0pCgogICAgICAgIG1vdmVzID0geyJ1cCI6ICgwLCAxKSwgImRvd24iOiAoMCwgLTEpLCAibGVmdCI6ICgtMSwgMCksICJyaWdodCI6ICgxLCAwKX0KICAgICAgICBzY29yZXMgPSB7fQoKICAgICAgICBmb3IgZGlyZWN0aW9uLCAoZHgsIGR5KSBpbiBtb3Zlcy5pdGVtcygpOgogICAgICAgICAgICBuZXdfeCwgbmV3X3kgPSB5b3VyX2hlYWRbMF0gKyBkeCwgeW91cl9oZWFkWzFdICsgZHkKICAgICAgICAgICAgbmV3X2hlYWQgPSAobmV3X3gsIG5ld195KQoKICAgICAgICAgICAgaWYgbmV3X3ggPCAwIG9yIG5ld194ID49IDExIG9yIG5ld195IDwgMCBvciBuZXdfeSA+PSAxMToKICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gLTFlOQogICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgIGlmIG5ld19oZWFkIGluIHlvdXJfYm9keV9zZXQ6CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICB2ZXRvID0gRmFsc2UKICAgICAgICAgICAgYm9udXMgPSAwLjAKCiAgICAgICAgICAgIGZvciBlbmVteSBpbiBlbmVteV9oZWFkczoKICAgICAgICAgICAgICAgIGVuZW15X3BvcyA9IGVuZW15WyJwb3MiXQogICAgICAgICAgICAgICAgZW5lbXlfbGVuZ3RoID0gZW5lbXlbImxlbmd0aCJdCiAgICAgICAgICAgICAgICBlbmVteV94LCBlbmVteV95ID0gZW5lbXlfcG9zCgogICAgICAgICAgICAgICAgY2FuX3JlYWNoID0gYWJzKGVuZW15X3ggLSBuZXdfeCkgKyBhYnMoZW5lbXlfeSAtIG5ld195KSA9PSAxCgogICAgICAgICAgICAgICAgaWYgY2FuX3JlYWNoOgogICAgICAgICAgICAgICAgICAgIGlmIGVuZW15X2xlbmd0aCA+PSB5b3VyX2xlbmd0aDoKICAgICAgICAgICAgICAgICAgICAgICAgdmV0byA9IFRydWUKICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICBib251cyArPSAyLjAKCiAgICAgICAgICAgIGlmIHZldG86CiAgICAgICAgICAgICAgICBzY29yZXNbZGlyZWN0aW9uXSA9IC0xZTkKICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgIHNjb3Jlc1tkaXJlY3Rpb25dID0gYm9udXMKCiAgICAgICAgcmV0dXJuIHNjb3JlcwogICAgZXhjZXB0OgogICAgICAgIHJldHVybiB7InVwIjogMC4wLCAiZG93biI6IDAuMCwgImxlZnQiOiAwLjAsICJyaWdodCI6IDAuMH0K'}
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
