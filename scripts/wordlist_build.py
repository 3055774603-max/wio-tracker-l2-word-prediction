# -*- coding: utf-8 -*-
"""Rebuild predict_wordlist.inc (v1.1) from the archived corpus.
Keeps the v1.0 3000 words byte-for-byte, appends to exactly 10000 words.
"""
import re, os
HERE = os.path.dirname(os.path.abspath(__file__))
V10  = os.path.join(HERE, 'src_snapshot', 'predict_wordlist_v1.0_3000words.inc')
OUT  = os.path.join(HERE, 'src_snapshot', 'predict_wordlist.inc')

def parse(p):
    return [w for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', open(p, encoding='utf-8').read())
            for w in lit.split('\\n') if w.strip()]
def load(fn):
    ws = [w.strip() for w in open(os.path.join(HERE, 'wordlist_source', fn), encoding='utf-8', errors='replace')]
    return [w for w in ws if re.fullmatch(r'[a-z]{2,14}', w)]

BAD = set("""porn porno pornography pornographic xxx hardcore erotic erotica hentai voyeur fetish bondage bdsm
milf shemale lolita viagra sexo escort escorts sex sexy nude nudes nudity pussy pussies penis vagina
boobs boob tits tit breasts dick dicks cock cocks cum jizz sperm semen orgasm orgy orgies
masturbate masturbating masturbation horny dildo vibrator condom condoms anal ass asses butt butts
slut sluts whore hooker prostitute prostitution fuck fucking fucked fucker shit bullshit wank wanking
bitch bitches rape raped incest molest pedo nazi nazis""".split())

old = parse(V10); assert len(old) == 3000
seen = set(old); words = list(old)
for src in (load('google-10000-english.txt'), load('google-20k.txt')):
    for w in src:
        if len(words) >= 10000: break
        if w in seen or w in BAD: continue
        seen.add(w); words.append(w)
    if len(words) >= 10000: break
assert len(words) == 10000 and words[:3000] == old
lines = [
 '// Word prediction list: 10000 most frequent English words, frequency order.',
 "// Source: google-10000-english (Peter Norvig's Google Web Trillion Word Corpus),",
 '// https://github.com/first20hours/google-10000-english (MIT)',
 '// v1.1: first 3000 entries byte-for-byte unchanged from v1.0;',
 '//       entries 3001..10000 appended from the same corpus (10k + 20k lists).',
 '//       Explicit adult/obscene terms filtered; words >14 chars dropped so no',
 '//       candidate can be truncated in the 320px / 3-button strip.',
 '// Format: newline separated, frequency descending, [a-z] only, max 14 chars.',
 'static const char kPredictWordList[] =']
for i in range(0, len(words), 12):
    lines.append('    "' + ''.join(w + '\\n' for w in words[i:i+12]) + '"')
lines.append('    ;')
open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
assert parse(OUT) == words
print('rebuilt', len(words), 'words ->', OUT)
