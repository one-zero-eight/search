import re

from catix.wiki.synth import Evidence, claims_of, text_sha


def test_claims_carry_the_hash_of_the_evidence_they_cite():
    ev = Evidence()
    ev.add("clause 2.2: up to 12 months", ["/regulations/x.md"])
    ev.add("clause 2.3: apply to the director", ["/regulations/x.md"])
    text = "## Duration\nLeave lasts up to 12 months [E1]. A student applies to the director [E2][E1].\n\nNo citation here."
    claims = claims_of(text, ev)
    assert [c["sentence"] for c in claims] == ["Leave lasts up to 12 months", "A student applies to the director"]
    assert claims[0]["evidence"] == [{"n": 1, "sha": text_sha("clause 2.2: up to 12 months"), "sources": ["/regulations/x.md"]}]
    assert claims[1]["cites"] == [2, 1]


def test_cites_beyond_the_evidence_are_not_claims():
    ev = Evidence()
    ev.add("only one", [])
    assert claims_of("Wrong [E5].", ev) == []
