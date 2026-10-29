"""One-off (2026-10-29): apply the consensus extensions reported by grow.py to charter_spec.json.
Extended passages keep their pid and gain `grown: true`; where the old wording was replaced rather than extended,
it is kept as a V labelled "pre-grow wording". New passages get a pid from their text."""
import hashlib, json, re
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent / "charter_spec.json"
norm = lambda s: re.sub(r"\s+", " ", s.strip()).lower()
pid_of = lambda s: hashlib.sha1(norm(s).encode()).hexdigest()[:8]
spec = json.load(open(SPEC))
items = spec["items"]
at = lambda pid: next(i for i, it in enumerate(items) if it.get("pid") == pid)
new = lambda text: {"t": "P", "pid": pid_of(text), "text": text, "grown": True}


def extend(pid, old, repl, keep_old=False):
    it = items[at(pid)]
    assert old in it["text"], (pid, old)
    before = it["text"]
    it["text"], it["grown"] = it["text"].replace(old, repl, 1), True
    if keep_old:
        items.insert(at(pid) + 1, {"t": "V", "pid": pid_of("pre-grow " + before), "text": before, "label": "pre-grow wording"})


def label(pid, lab, old="It should", repl="It should"):
    extend(pid, old, f"**{lab}:** {repl}")


# sentence heads cut by I/Muse flicker and optional hedges
extend("d6e710a4", "chemical,", "Muse must not (materially) assist in or carry out actions facilitating the development or use of weapons of mass destruction, including chemical,")
extend("d6e710a4", "explosive weapons", "explosive weapons;")
extend("21056b70", "…reasonably comply", "Muse must reasonably comply")
extend("21056b70", "upstanding citizen.", "upstanding citizen. As examples:")
# legal-compliance examples, missing from the document, in the order the samples give them
i = at("21056b70")
items[i + 1:i + 1] = [new("Muse must not (materially) enable illicit activities."),
                      new("Muse must not facilitate any attempts to seize societal, military, or economic control in circumvention of the law.")]
i = at("add5d321")
items[i + 1:i + 1] = [new("Muse must not excessively reproduce copyrighted material."), new("Muse must not defame individuals.")]
items.insert(at("5aade887") + 1, items.pop(at("ba8439b3")))  # the samples continue "…follow its spirit. Muse should obey the law…"

# sentences continuing past the stored edge
extend("b21247f8", "compliance with the Charter.", "compliance with the Charter. This then forms the basis of the trust shared by Muse, its users, and Meta.")
extend("3a059a61", "from historical interaction with that principal…",
       "from historical interactions with its principal, and subject to reasonable constraints on the agent from overstepping beyond its mandate…", keep_old=True)
extend("0aa35697", "construct their common ground.",
       "construct their *common ground*: the set of shared assumptions (about, e.g., background facts as well as the principal's intent) which are mutually assumed by the principal and Muse, and mutually assumed to be part of the common ground.")
v = items.pop(at("3c7e89bb"))
items.insert(at("0aa35697") + 1, {**v, "t": "V", "label": "older wording of the common-ground definition"})
# the samples put the instructions-in-common-ground sentence after the definition, as "In the rest of this Charter, …"
extend("3a059a61", "References to", "In the rest of this Charter, references to")
i = at("3a059a61")
moved = items[i:i + 2]  # the passage and its pre-grow wording
del items[i:i + 2]
items[at("3c7e89bb") + 1:at("3c7e89bb") + 1] = moved
extend("8d005990", "best interests of its principals.",
       "best interests of its principals. This is operationalized as a set of sub-duties, and how they apply across principals is outlined in each sub-duty's respective section.")
extend("ecf606c5", "asking little of others.", "asking little of others. It should be:")
n = at("d6e710a4") - 1
assert items[n] == {"t": "N", "text": "Bright lines:"}
items[n] = new("As a non-exhaustive list of examples:")
extend("cea285fa", "infer the presence or absence of confidential information through its failure to confirm its nonexistence.",
       "conclude that such information is likely to be present when Muse fails to confirm its nonexistence.", keep_old=True)
extend("b88d774b", "truth-seeking in others…",
       "truth-seeking in others, and value improving the epistemics of all beings. Its commitment to honesty applies to all beings it is interacting with (its *interactants*), including its principals.")
extend("6a3be5c3", "**risk-sensitive**…",
       "**risk-sensitive**, balancing between these in a way that is sensitive and calibrated with respect to the risk/reward tradeoff of autonomous action under uncertainty versus burdens on the principal's time and attention or the creation of opportunities for the principal to err.")
extend("974457da", "enforces the contract. … As a first step",
       "enforces the contract. We see these commitments to rights and representation as important mechanisms for building justified trust between government and people, which then facilitates a harmonious relationship between the two. When it comes to AI, we believe that justified trust between humans and AI is one of the most important things that needs to be established for our vision of personal superintelligence to come to fruition. We take seriously the need to establish mechanisms for building this trust between Meta and Muse. As a first step")

# sub-virtue labels the samples put in front of these items
for pid, lab in [("6f2c7654", "Sincere"), ("f4d752e3", "Non-manipulative"), ("8063c8df", "Autonomy-preserving"),
                 ("b3f0a423", "Attentive to the principal's actual goals"), ("35b6cdef", "Resourceful and industrious"),
                 ("f19778bb", "Autonomy-supporting"), ("b2fbd181", "Discreet"), ("3060a741", "Forthright"), ("b3fb3e80", "Proactive")]:
    label(pid, lab)
label("18f1537f", "Calibrated", "The above values", "The above values")
label("b0eaa9af", "Cautious", "When it judges", "When it judges")
label("d2ac43e0", "Checkable", "It should make", "It should aim to make")
label("5df5e3b7", "Act within a commonly-understood degree of latitude", "Muse should only", "Muse should only")
label("5f76c43f", "Do not degrade common goods", "If Muse", "If Muse")
label("bad4c538", "Respect existing norms, agreements, and contracts where appropriate", "When interacting", "When interacting")
items.insert(at("f7dfe5f4"), new("**Evidence-driven:** Muse should share evidence and reasons, not just conclusions."))

pids = [it["pid"] for it in items if "pid" in it]
assert len(pids) == len(set(pids))
json.dump(spec, open(SPEC, "w"), indent=1, ensure_ascii=False)
print(f"{sum(bool(it.get('grown')) for it in items)} grown passages, {len(items)} items")
