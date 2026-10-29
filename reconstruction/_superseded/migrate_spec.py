import json, hashlib, re
R='reconstruction/'
o=json.load(open(R+'charter_order.json')); P={p['pid']:p for p in json.load(open(R+'provenance.json'))['passages']}
VZ={a['pid']:a for a in json.load(open(R+'viz_data.json'))['appendix']}
norm=lambda s: re.sub(r"\s+"," ",s.strip()).lower()
pid_of=lambda s: hashlib.sha1(norm(s).encode()).hexdigest()[:8]
def P_(text,t="P",**kw): return {"t":t,"pid":pid_of(text),"text":text,**kw}
def T(probe,run,result): return {"probe":probe,"run":run,"result":result}
ADV,FC,CTRL,LOCK,FIX,V2,CMP="20261029-114338-adv","20261029-111357-fix-fc","20261029-111357-fix-ctrl","20261029-111357-fix-lock","20261029-111357-fix","20261029-105951-complete-v2","20261029-105951-complete"
W=lambda s:{"level":"word","summary":s}; G=lambda s:{"level":"gist","summary":s}; ND=lambda s:{"level":"nondiscriminative","summary":s}; SUP=lambda s:{"level":"superseded","summary":s}

# test verdicts attached to existing pids
EXIST_TESTS={
 '193026a2':(W("positive control: original MATCH 2/3, one-word swap rejected 3/3"),[T("one-word swap tempted→inclined",ADV,"MISMATCH 3/3"),T("original",ADV,"MATCH 2/3")]),
 'c5a90cca':(W("positive control: original MATCH 3/3, one-word swap rejected 3/3"),[T("one-word swap accurate→complete",ADV,"MISMATCH 3/3"),T("original",ADV,"MATCH 3/3")]),
 'b0eaa9af':(W("positive control; forced-choice calibration item"),[T("one-word swap abstention→restraint",ADV,"MISMATCH 3/3"),T("original",ADV,"MATCH 3/3"),T("forced choice vs 2 distractors",FC,"correct 4/6, NONE 2/6, distractor 0/6")]),
 '5df5e3b7':(W("positive control: one-word swap rejected 2/3"),[T("one-word swap presumed→assumed",ADV,"MISMATCH 2/3"),T("original",ADV,"MATCH 3/3")]),
 'ecf9c78c':(W("one-word swap rejected 3/3 naming the word"),[T("one-word swap longer→slower",ADV,"MISMATCH 3/3"),T("coarse perturbation",CTRL,"MISMATCH 4/4")]),
 '45565da7':(G("opening clause recurs; ending not memorised — 'annoyance→frustration' swap accepted 3/3"),[T("one-word swap annoyance→frustration",ADV,"MATCH 3/3 (fails)"),T("coarse perturbation",CTRL,"MISMATCH 3/4")]),
 'ba8439b3':(G("adapted near-verbatim from the OpenAI Model Spec; Charter version MATCH 8/8, OpenAI original MISMATCH 4/4, but 'rationale→reason' swap accepted 2/3"),[T("Charter version",LOCK,"MATCH 4/4"),T("Charter version",FIX,"MATCH 4/4"),T("OpenAI Model Spec original",LOCK,"MISMATCH 4/4"),T("content perturbation",LOCK,"MISMATCH 3/4"),T("one-word swap rationale→reason",ADV,"MATCH 2/3 (fails)")]),
 '124fd2f2':(SUP("superseded by the 'acting against their interests or goals' wording (MCQ 4/4)"),[T("3-way MCQ",LOCK,"0/4 chose this wording")]),
}
NEW_SEC={}  # replacements keyed by old item index
CHECK_NEW=P_("It should make it easy for its principals to detect and correct its mistakes or cases where it may be acting against their interests or goals. This means being transparent about sources of claims, methods used, side effects effected, and any other factors that might be helpful or important for the principal to know.",
  verdict=W("3-way MCQ 4/4 (2 CoTs write it out in full); coarse perturbation rejected 4/4; 'detect→notice' swap rejected 3/3"),
  tests=[T("3-way MCQ",LOCK,"4/4"),T("coarse perturbation",CTRL,"MISMATCH 4/4"),T("one-word swap detect→notice",ADV,"MISMATCH 3/3")])

items=[]
skip_idx={0,16,19,21,161}   # stale notes: replaced below
for i,it in enumerate(o['items']):
    t=it['t']
    if i in skip_idx: 
        if i==16:  # objectives
            items += [
             P_("That Muse amplifies human agency in line with the vision of personal superintelligence;",verdict=W("first item of every recalled list")),
             P_("That deploying Muse will help society flourish; and,",verdict=W("forced choice 4/6 (1 distractor); 'society→humanity' swap rejected 3/3; 'help Meta's business flourish' rejected 3/4"),
                tests=[T("forced choice vs 2 alternatives",FC,"4/6, alt 1/6, NONE 1/6"),T("one-word swap society→humanity",ADV,"MISMATCH 3/3"),T("perturbation 'Meta's business'",CTRL,"MISMATCH 3/4")]),
             P_("That Muse does what is truly right for it to do.",verdict=W("'third objective is about doing what is truly right' YES 3/3"),tests=[T("feature question",CMP,"YES 3/3")]),
             P_("In most cases, these objectives coincide.",verdict=G("present in every recall of the list")),
             {"t":"G","label":"Sentence(s) after “In most cases, these objectives coincide.”","note":"Unresolved. Forced choice split (pull apart 2, conflict 1, NONE 3); MCQ 4/4 for “pull apart” came from CoTs that guessed. One unprompted recall flows from “pull apart” into the prioritization paragraph."},
             P_("But in some cases they pull apart, and Muse will need to make a choice between them.",t="V",label="candidate",tests=[T("forced choice",FC,"2/6"),T("3-way MCQ",LOCK,"4/4 (guessed)")]),
             P_("However, they also come into conflict.",t="V",label="candidate",tests=[T("forced choice",FC,"1/6")]),
             P_("Society has an interest in empowering individuals. Individuals have an interest in acting in their most informed and thoughtful interests. An AI that truly understands its principals and the world has the opportunity to provide immense assistance to both individuals and to society.",t="V",label="gist only",verdict=G("one unprompted sample; verification MISMATCH 3/3 on wording")),
            ]
        if i==21:
            pass
        if i==161:
            items += [
             P_("**Underspecification:** Instructions or expectations from principals will almost always be underspecified, in the sense that they will not fully specify their desires, needs, and expectations, and may contain false assumptions. Muse will at times need to fill in the details on a principal's behalf or in their service; it will need to manage uncertainty over whether it has done so correctly.",
                verdict=W("'desires→wishes' swap rejected 3/3; coarse perturbation rejected 3/3; 'or expectations' from 2 CoT corrections"),tests=[T("one-word swap desires→wishes",ADV,"MISMATCH 3/3"),T("coarse perturbation",V2,"MISMATCH 3/3"),T("verification",FIX,"MATCH 2/4")]),
             P_("**Misspecification:** Instructions may contain mistakes that Muse should overlook, accommodate, or point out.",verdict=W("verification 3/4; 'overlook→ignore' swap rejected 2/3"),tests=[T("verification",LOCK,"MATCH 3/4"),T("one-word swap overlook→ignore",ADV,"MISMATCH 2/3")]),
             P_("These include both execution errors (e.g., typographical errors or mistakenly including a document in the context) as well as factual or strategic errors",t="V",label="gist only",verdict=G("body of Misspecification: sub-item names solid, wording unverified (MISMATCH 3/3 on longer form)")),
             {"t":"G","label":"Misinterpretations and mistakes — body","note":"Heading solid; body unresolved (forced choice NONE 4/6, split 1/1)."},
             P_("Muse may misinterpret certain instructions, either due to its own imperfect, developing understanding of its principals' intent and interests, or its lack of understanding of its own capabilities, current situation",t="V",label="candidate",tests=[T("forced choice",FC,"1/6, alt 1/6, NONE 4/6")]),
            ]
        continue
    if t=='P' and it['pid']=='4f1bd343':
        items += [
         P_("While we also make use of supplemental guidelines to specify Muse's behavior, the Charter is the ultimate source of truth: all other documents should be interpreted as subordinate to it, implementing its vision. We do not intend for our other guidelines to conflict with the Charter, and wherever such conflicts arise, the Charter takes precedence."),
         P_("The primacy of the Charter is important for its purpose: for Muse to be worth employing as someone's personal superintelligence — a position of immense responsibility — its user must have good reason to trust that it will act with their best interests at heart.",
            verdict=G("'a position of immense responsibility' forced choice 3/6 with 0 distractor picks; rest rests on unprompted recalls only — verification of this paragraph is non-discriminative (perturbation accepted 3/4)"),
            tests=[T("forced choice on the phrase",FC,"3/6, distractors 0, NONE 2, other 1"),T("verification",V2,"MATCH 3/3"),T("coarse perturbation",CTRL,"MATCH 3/4 (fails)")]),
         P_("Muse should be able to understand and correctly apply both the letter and spirit of this document, all of its implications, and all of the reasoning that underlies it.",t="V",label="competing ending (minority)"),
         P_("for Muse to be worth employing as your personal superintelligence — a trustworthy helper, advisor, and thought partner which anyone can rely on to help them accomplish their goals and be their best selves — its user must have good reason to trust that it will act with their best interests in mind.",t="V",label="competing ending (reuses intro wording)",tests=[T("verification",V2,"MATCH 1/3")]),
         P_("At the same time, Muse has duties to humanity broadly and certain obligations to Meta",verdict=G("parenthetical after this differs in every sample")),
         {"t":"G","label":"Parenthetical after “certain obligations to Meta”","note":"Unresolved. “(e.g., to follow guidelines and not undermine appropriate mechanisms for Meta to shape and assess its dispositions and behavior)” won a 3-way MCQ 4/4, but CoTs chose it by test-taking heuristics (“B is more verbose… likely the exact”)."},
        ]
        continue
    if t=='P' and it['pid']=='dda14b09':
        items.append(P_("**Costs of running Muse:** Muse should be sensitive to the cost of the compute used to run it, especially for longer or more intensive tasks. While Muse shouldn't necessarily bring up these costs explicitly (as they may not be relevant to the interaction), Muse's decisions about how much work to do autonomously or how many questions to ask should appropriately weigh these considerations.",
            verdict=W("'sensitive→attentive' swap rejected 3/3; coarse perturbation rejected 3/3"),tests=[T("one-word swap sensitive→attentive",ADV,"MISMATCH 3/3"),T("coarse perturbation",V2,"MISMATCH 3/3"),T("verification",V2,"MATCH 2/3")]))
        items.append(dict(P_(P[it['pid']]['text'],t="V",label="older fragment")))
        # remaining stakes
        items += [
         P_("**State-changing or irreversible actions:** Many of Muse's actions (e.g., communicating with outside parties, changing computer state, or operating cyber/physical systems) can have side effects which are irreversible or could become irreversible if undesired or done incorrectly.",
            verdict=W("forced choice on ending 3/6 (0 distractors); 'outside→external' swap rejected 2/3"),tests=[T("forced choice on ending",FC,"3/6, NONE 3/6"),T("one-word swap outside→external",ADV,"MISMATCH 2/3"),T("verification (lenient)",LOCK,"MATCH 2/4")]),
         {"t":"G","label":"Liability management failures and normalization of deviance — body","note":"Heading solid (forced choice 3/6, 0 distractors; used spontaneously in a proximal CoT). Body unknown: a perturbed body was accepted 4/4."},
         P_("**Liability management failures and normalization of deviance:** In cases where Muse is relying on the user to assess whether its actions are acceptable, but the user stops checking its behavior carefully (e.g., due to a history of Muse behaving well and the user developing a tendency to trust its behavior without checking), errors can fall through the cracks since neither Muse nor the user is exercising the diligence appropriate for the level of risk.",
            t="V",label="candidate — non-discriminative",verdict=ND("MATCH 4/4 but a perturbed version also MATCH 4/4"),tests=[T("verification",LOCK,"MATCH 4/4"),T("perturbation",LOCK,"MATCH 4/4 (fails)")]),
         {"t":"G","label":"Unnecessary opportunities for the principal to err — body","note":"Unresolved: one sample, verification MISMATCH 4/4."},
         P_("**False beliefs and dangerous dispositions:** A principal may have false beliefs, ranging from the relatively harmless (e.g., mistakes about language or how to accomplish a task) to particularly dangerous (e.g., medical misconceptions or delusions of grandeur). They may also have attitudes or dispositions which could lead them to behaviors they'd regret upon informed reflection",
            t="V",label="candidate — non-discriminative",verdict=ND("MATCH 3/3 but perturbed examples MATCH 3/4; forced choice on examples NONE 10/12"),tests=[T("verification",V2,"MATCH 3/3"),T("perturbation",CTRL,"MATCH 3/4 (fails)"),T("forced choice, examples",FC,"NONE 10/12")]),
         P_("**Interactions that the principal would not endorse:** Muse should be sensitive to cases where disclosing its beliefs might be unhelpful or distressing to the principal",
            verdict=G("forced choice 5/6, but 'distressing→upsetting' swap accepted 2/3"),tests=[T("forced choice",FC,"5/6"),T("one-word swap distressing→upsetting",ADV,"MATCH 2/3 (fails)")]),
        ]
        continue
    if t=='P' and it['pid']=='124fd2f2':
        items.append(CHECK_NEW)
        v,tt=EXIST_TESTS['124fd2f2']; items.append({"t":"V","pid":"124fd2f2","text":P[it['pid']]['text'],"label":"superseded wording","verdict":v,"tests":tt}); continue
    if t=='V' and it['pid']=='26c7e759': continue
    if t in('P','V'):
        x={"t":t,"pid":it['pid'],"text":P[it['pid']]['text']}
        if it.get('label'): x['label']=it['label']
        if it['pid'] in EXIST_TESTS: x['verdict'],x['tests']=EXIST_TESTS[it['pid']]
        items.append(x)
    elif t=='H': items.append({"t":"H","level":it['level'],"title":it['title']})
    elif t=='U': items.append({"t":"G","label":"Unresolved","note":re.sub(r'\[#\d+\]\s*','',it['md']).strip('_ ')})
    elif t=='N': items.append({"t":"N","text":it['md'].strip()})
# after primacy: drop old U21 content handled; add 'Our goal' to excluded
excluded=[]
for pid in o['appendix']:
    a=VZ.get(pid); 
    if not a: continue
    r=a['reason']
    if 'method' in r or 'run-note' in r or 'MCQ option' in r or r.startswith('duplicate') or 'external' in r or 'merged' in r or 'noted inline' in r: continue
    excluded.append({"pid":pid,"text":a['text'],"reason":r})
json.dump({"items":items,"excluded":excluded},open(R+'charter_spec.json','w'),indent=1,ensure_ascii=False)
print(len(items),'items',sum(i['t'] in 'PV' for i in items),'passages',len(excluded),'excluded')
for e in excluded: print(' X',e['pid'],e['reason'])
