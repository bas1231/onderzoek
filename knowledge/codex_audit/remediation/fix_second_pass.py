from pathlib import Path
import json
r=Path('/tmp/codex-remediation-80a5ff7');d=Path('/home/leonh/prediction_research_prod/knowledge/codex_audit/remediation')
(d/'SECOND_PASS_CHARTER.json').write_text(json.dumps({'objective':'Bevestigde schijnlevering en ongeldige post-event marketstate fail-closed afhandelen in voorstelkopie.','production_mutation':False,'allowed_paths':['/tmp/codex-remediation-80a5ff7','knowledge/codex_audit'],'acceptance_criteria':['Nieuwe userturn vereist voor leveringsbevestiging.','Foreign ticker/nonfinite poststate geeft UNPROVEN.','Positieve bestaande gedragstests blijven behouden.'],'max_attempts':3},indent=2)+'\n')
p=r/'control/tampermonkey_multichat/prediction-chat-wake.user.js';s=p.read_text();s=s.replace('    button.click();\n    await sleep(650);','''    // A cleared editor is not a delivery receipt: require a new user turn.
    const normalize = value => String(value || '').replace(/\\s+/g, ' ').trim();
    const matchingTurns = () => Array.from(document.querySelectorAll('[data-message-author-role="user"]'))
      .filter(node => normalize(node.innerText || node.textContent) === normalize(text)).length;
    const before = matchingTurns();
    button.click();
    for (let i = 0; i < 20; i += 1) {
      await sleep(250);
      if (matchingTurns() > before) return true;
    }
    status('geen nieuwe userturn bevestigd; levering onbewezen', true);
    return false;
    /* Legacy editor-only heuristic removed.
    await sleep(650);''');s=s.replace('    return true;\n  }\n\n  async function ack(', '    return true; */\n  }\n\n  async function ack(');start=s.index('    /* Legacy editor-only');end=s.index(' */',start)+3;s=s[:start]+s[end:];p.write_text(s)
p=r/'tests/audit/test_reliability_regressions.py';s=p.read_text().replace("let composer={value:scenario==='draft'?'USER DRAFT':''}, sent=[], polls=0;","let composer={value:scenario==='draft'?'USER DRAFT':''}, sent=[], polls=0;\nconst document={querySelectorAll:()=>sent.map(text=>({textContent:text}))};");p.write_text(s)
p=r/'control/weather/market_reaction.py';s=p.read_text();needle='    if any(_gap_straddles(g, t0 - max_pre_age_ms, end) for g in gaps):';new='''    if pre:
        for state in ordered:
            if not t0 <= state.ts_ms <= end:
                continue
            if state.ticker != pre[-1].ticker:
                reasons.append("MIXED_MARKET_TICKERS")
            prices = (state.yes_bid, state.yes_ask, state.no_bid, state.no_ask)
            quantities = (state.yes_bid_qty, state.no_bid_qty)
            if any(p is not None and (not p.is_finite() or not 0 <= p <= 1) for p in prices):
                reasons.append("INVALID_POST_EVENT_BOOK")
            if any(q is not None and (not q.is_finite() or q < 0) for q in quantities):
                reasons.append("INVALID_POST_EVENT_BOOK")
    if any(_gap_straddles(g, t0 - max_pre_age_ms, end) for g in gaps):''';assert needle in s;s=s.replace(needle,new);p.write_text(s)
