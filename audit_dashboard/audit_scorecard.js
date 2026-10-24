(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AuditScorecard = api;
})(typeof window === 'undefined' ? globalThis : window, function () {
  'use strict';
  var state = { verdicts: null, error: null, loading: null };
  var explanations = {
    label: 'MONEY-READY means every required evidence gate plus operator approval passes. CANDIDATE means the published research gates pass, not a buy instruction. FAIL means a gate failed or required evidence is missing. ELI5: promising homework is not permission to spend money.',
    compound: 'Compound return needs a dated, capital-constrained equity curve including open-position marks, position sizes and costs. Multiplying overlapping trade percentages is not an account return. ELI5: count the money actually in one wallet, not the same dollar spent many times.',
    pf: 'Profit factor divides total net winning returns by total net losing returns. A day-cluster bootstrap resamples whole days together for the 95% interval. An undefined upper end is not unlimited profit. S2 requires PF >=1.5; S3 requires the lower bound >=1.2. ELI5: how many dollars came back for each dollar lost, with a range for uncertainty.',
    days: 'Trades closed on the same day share market conditions. Distinct days show how much independent history exists. ELI5: 100 guesses on one day are not 100 different weather forecasts.',
    costs: 'Two-times-cost stress asks whether the edge survives more expensive execution. S10 requires PF >=1.3. Scenario costs are not measured broker fills. ELI5: would it still work if the fees were bigger?',
    mdd: 'Maximum drawdown is the largest peak-to-trough loss in a dated funded equity curve. S5 requires <=20%. Missing portfolio marks cannot be replaced by closed-trade sums. ELI5: the worst fall from your wallet high-water mark.',
    concentration: 'Top-symbol share shows dependence on one instrument. S11 requires <=30% and PF >=1.3 after removing that instrument. ELI5: one lucky stock must not carry the whole team.',
    wr: 'Win rate is hidden for fewer than 20 closed observations. It does not measure the size of wins or losses and does not prove an edge. ELI5: winning often can still lose money if losses are bigger.',
    horizon: 'A bar timeframe is not a maximum holding period. The plan needs an explicit deadline as well as TP and SL. Missing deadlines stay unverified. ELI5: say when you give up waiting, not just when you check the price.',
    exits: 'TP (take profit) and SL (stop loss) are stored exit rules, not predicted prices or guaranteed fills. LONG requires SL < entry < TP; SHORT requires TP < entry < SL. Gaps and costs can worsen loss. ELI5: planned doors out, not promises.',
    payoff: 'Target distance / stop distance is the planned gross reward-to-risk ratio, not expected profit. It assumes fills exactly at the barriers. Profitability still needs the probability of reaching each exit, time exits, fees and gaps. ELI5: a bigger prize does not mean you are more likely to win it.',
    certainty: 'No calibrated probability of future profit is available. Signal confidence and historical win rate are not forecast certainty. ELI5: a model score is not a weather forecast tested for accuracy.'
  };
  var gateHelp = {
    D1: ['Are the numbers believable?', 'Reject impossible prices and placeholder values. Like checking that a thermometer did not report a million degrees.'],
    D2: ['Is the feed actually fresh?', 'The source observations must change on schedule, not just the file timestamp. Like replacing a newspaper cover while leaving last month inside.'],
    D3: ['Can we prove the order of events?', 'Observation must precede the real entry and exit. Like requiring a prediction to be written before opening the answer envelope.'],
    D4: ['Was the market open?', 'Use the instrument exchange calendar. Like rejecting a shop receipt issued when the shop was closed.'],
    D5: ['Did we disclose removed rows?', 'Every exclusion needs a reason. Like showing all spoiled ingredients removed, not quietly changing the recipe.'],
    D6: ['Does another price source agree?', 'Cross-check a sample against independent market data. Like weighing a parcel on a second scale.'],
    L1: ['Could the entry really happen?', 'Do not use a signal-bar price that was already gone when the signal became known. Like not buying a winning ticket after the draw.'],
    L2: ['Did tomorrow leak into today?', 'Features must use only information available then. Like taking an exam without the answer key.'],
    L3: ['Did the old universe include failures?', 'Use names that existed at that date, including delisted ones. Like measuring a school using all entrants, not only graduates.'],
    L4: ['Were the inputs available then?', 'Use original economic reports, not later revisions. Like judging a forecast using the weather report people actually had that morning.'],
    L5: ['Were the rules frozen first?', 'Parameters and selection must be fixed before the unseen test. Like writing the rules before the race.'],
    L6: ['Was the regime knowable?', 'A bull/bear filter must not use later data to rename the past. Like not changing yesterday weather label after seeing the result.'],
    R1: ['Which exit was reached first?', 'Replay the price path, not just the final quote. Like checking the whole race video rather than a finish photo.'],
    R2: ['What if target and stop share a candle?', 'Without finer evidence, count the stop first. Like using the less flattering interpretation of a blurry video.'],
    R3: ['Does a SHORT gain when price falls?', 'SHORT gross return is (entry minus exit) divided by entry. Like buying back something cheaper than you sold it.'],
    R4: ['Did the same money get reused twice?', 'Reject overlapping same-book symbol signals. Like not booking the same hotel room for two guests at once.'],
    R5: ['Did we count a trade twice?', 'Unique IDs and event keys stop duplicate credit. Like refusing two receipts for one purchase.'],
    R6: ['Are mass closing times suspicious?', 'Check closing clusters and independent dates. Like doubting 100 supposedly independent exams with the same timestamp.'],
    R7: ['Is zero a real flat or a placeholder?', 'An unresolved price lookup must not become a successful breakeven. Like not treating a blank grade as a pass.'],
    R8: ['Did we see the whole history?', 'Reconcile a full export with the DB, not just the displayed cap. Like reading all pages before judging a book.'],
    C1: ['Were all real costs paid?', 'Include fees, spread, funding, borrow, roll and impact where relevant. Like subtracting fuel and tolls from delivery income.'],
    C2: ['Would higher costs erase the edge?', 'Repeat with twice the applicable costs. Like testing whether a restaurant still works if ingredients get more expensive.'],
    S1: ['Do we have enough independent observations?', 'At least 100 independent trades, 500 to scale. Like testing a recipe with many diners on different days, not one table of friends.'],
    S2: ['Are wins large enough after costs?', 'Net PF must reach 1.5 for the main gate. Like earning at least $1.50 of gains for each $1 of losses.'],
    S3: ['Does the cautious estimate still work?', 'The day-clustered PF interval lower bound must reach 1.2. Like checking the bottom of the plausible range, not the sales pitch.'],
    S4: ['How often did it win?', 'At least 50%, hidden below n=20. Like counting correct answers, but remembering a wrong answer can cost much more.'],
    S5: ['How painful was the worst fall?', 'Maximum funded-book drawdown must be no more than 20%. Like measuring the deepest hole before celebrating the final hill.'],
    S6: ['Did it beat random timing?', 'Same-market random entries with the same costs and exits must be beaten at the required percentile. Like racing someone given the same track and shoes.'],
    S7: ['Would shuffled signals do as well?', 'Shuffle dates/labels under a defensible null; p must be below 0.05. Like checking whether mixing answer sheets removes the advantage.'],
    S8: ['Did we search until we got lucky?', 'DSR above 0.95 needs the family trial history. Like allowing for the fact that one of thousands of lottery tickets will win.'],
    S9: ['Does picking the best backtest backfire?', 'PBO below 0.2 uses all competing trial return histories. Like selecting a champion repeatedly and checking whether it then loses the next race.'],
    S10: ['Does it survive double costs?', 'PF must remain at least 1.3 at twice the applicable costs. Like leaving room for a price increase rather than needing perfect conditions.'],
    S11: ['Is one symbol doing all the work?', 'Top-symbol share at most 30%; without it PF at least 1.3. Like a sports team that must still compete when its star is absent.'],
    S12: ['Does it work beyond one lucky month?', 'Positive PF in at least 70% of months, no month over 40% of profit, and at least two regimes. Like a roof that works in more than one season.'],
    S13: ['Can the intended size actually trade?', 'Liquidity and market impact must support the intended capital. Like fitting a truck through a gate designed for a bicycle.'],
    F1: ['Were future-test rules sealed?', 'Record the rules hash before the first forward signal. Like sealing the exam paper before marking starts.'],
    F2: ['Can anyone rewrite losing forecasts?', 'Append-only, timestamped, hash-linked observations. Like a tamper-evident notebook.'],
    F3: ['Has it run long enough in real time?', 'At least 60 trading days and 50 forward trades for review. Like test-driving a car through months of weather rather than around the block.'],
    F4: ['Did future results agree?', 'Forward PF at least 1.3 and within historical uncertainty. Like seeing the recipe work in a new kitchen, not only in the original demonstration.']
  };
  function gateExplanation(key) {
    return gateHelp[key] || ['Evidence requirement', 'No beginner explanation supplied; inspect the versioned rules and evidence reason.'];
  }
  function finite(value) { return typeof value === 'number' && Number.isFinite(value); }
  function number(value, places) { return finite(value) ? value.toFixed(places === undefined ? 2 : places) : 'unverified'; }
  function percent(value) { return finite(value) ? number(value) + '%' : 'unverified'; }
  function interval(value) {
    return Array.isArray(value) && value.length === 2 ? '[' + number(value[0]) + ', ' + number(value[1]) + ']' : 'unverified';
  }
  function stamp(value) {
    if (typeof value !== 'string' || !/[T ][\d:.]+(?:Z|[+-]\d{2}:\d{2})$/i.test(value.trim())) return null;
    var parsed = Date.parse(value);
    return Number.isFinite(parsed) ? new Date(parsed).toISOString() : null;
  }
  function node(tag, text, className) {
    var item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  }
  function help(label, key) {
    var detail = node('details', undefined, 'asc-help');
    detail.append(node('summary', label), node('p', explanations[key]));
    return detail;
  }
  function field(parent, label, value, key) {
    var line = node('div', undefined, 'asc-field');
    line.append(key ? help(label, key) : node('span', label), node('strong', value));
    parent.append(line);
  }
  function validate(data, snapshot) {
    if (!data || data.schema_version !== 1 || !data.source ||
        !data.classes || !Array.isArray(data.strategies) || !Array.isArray(data.top_verified) ||
        !/^[a-f0-9]{64}$/.test(data.rules_hash || '') || !stamp(data.generated_at)) {
      throw new Error('Invalid verdicts contract');
    }
    if (snapshot && stamp(snapshot.generated_at) !== stamp(data.generated_at)) {
      throw new Error('Verdicts do not match the dashboard snapshot');
    }
    if (data.top_verified.some(function (s) {
      return !['MONEY-READY', 'CANDIDATE'].includes(s.label) || !finite(s.score);
    })) throw new Error('Invalid verified strategy label');
    return data;
  }
  function pickPlan(pick) {
    var direction = String(pick.direction || '').toUpperCase();
    if (direction === 'BUY') direction = 'LONG';
    if (direction === 'SELL') direction = 'SHORT';
    function price(value) {
      if (value === null || value === undefined || value === '') return null;
      var v = Number(value);
      return Number.isFinite(v) && v > 0 ? v : null;
    }
    var entry = price(pick.entry_price), tp = price(pick.take_profit), sl = price(pick.stop_loss);
    var geometry = entry !== null && tp !== null && sl !== null &&
      (direction === 'LONG' ? sl < entry && entry < tp : direction === 'SHORT' && tp < entry && entry < sl);
    var hours = price(pick.max_hold_hours);
    var deadline = stamp(pick.expires_at);
    var horizon = hours ? number(hours) + ' hours maximum (source rule)' :
      deadline ? 'Deadline ' + deadline : 'unverified: no maximum holding rule supplied';
    return { direction: direction || 'unverified', entry: entry, tp: tp, sl: sl,
      reward_pct: geometry ? Math.abs(tp-entry)/entry*100 : null,
      risk_pct: geometry ? Math.abs(sl-entry)/entry*100 : null,
      reward_risk: geometry ? Math.abs(tp-entry)/Math.abs(sl-entry) : null,
      geometry: geometry, horizon: horizon, signal_at: stamp(pick.timestamp || pick.signal_time) };
  }
  function effectiveHealth(stats, data, now) {
    if (stats.health === 'BROKEN' || stats.health === 'EMPTY') return stats.health;
    var updated = stamp(data && data.source && data.source.snapshot_updated_at);
    if (!updated) return 'BROKEN';
    var age = ((now === undefined ? Date.now() : now) - Date.parse(updated)) / 86400000;
    if (age < -5 / 1440) return 'BROKEN';
    return age > 7 ? 'STALE' : stats.health;
  }
  function filterOwned(strategies, keys) {
    function sourceKey(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
    return strategies.filter(function (s) {
      return keys.some(function (k) {
        var matching = strategies.filter(function (other) {
          return other.asset_class === k.asset_class && other.strategy === k.strategy &&
            sourceKey(other.source_system) === sourceKey(k.source);
        });
        var sources = new Set(matching.map(function (other) { return other.source_system; }));
        return sources.size === 1 && s.asset_class === k.asset_class && s.strategy === k.strategy &&
          sourceKey(s.source_system) === sourceKey(k.source) &&
          (!k.direction || s.direction === k.direction);
      });
    });
  }
  function coverage(data) {
    var s = data.source;
    return 'Data covers: ' + (s.first_close || 'unverified') + ' to ' + (s.last_close || 'unverified') +
      ', ' + number(s.input_closed_n, 0) + ' of ' + (s.total_known ? number(s.total_closed_n, 0) : 'unknown total') +
      ' closed picks. Scope: ' + (s.scope || 'published snapshot only') +
      '. Exclusions are policy screens, not allegations of fraud.';
  }
  function card(stats, title) {
    var box = node('article', undefined, 'asc-card');
    var measured = effectiveHealth(stats, state.verdicts);
    var health = ['OK', 'EMPTY', 'STALE', 'BROKEN'].includes(measured) ? measured : 'BROKEN';
    box.append(node('h4', title + ' | ' + health));
    if (health === 'BROKEN') box.append(node('p', 'Endpoint unavailable / Access denied. Infrastructure details withheld.', 'asc-warning'));
    field(box, 'Compound Return', percent(stats.compound_return_pct), 'compound');
    if (stats.inconsistent) box.append(node('p', 'inconsistent: compound and trade sum disagree in sign', 'asc-warning'));
    field(box, 'Closed n / W / L', number(stats.n, 0) + ' / ' + number(stats.wins, 0) + ' / ' + number(stats.losses, 0), 'wr');
    field(box, 'Win rate', stats.n < 20 ? 'n<20' : percent(stats.win_rate), 'wr');
    field(box, 'PF (95% day CI)', number(stats.pf) + ' ' + interval(stats.pf_ci95), 'pf');
    field(box, 'PF at 2x costs', number(stats.pf_2x_cost), 'costs');
    field(box, 'Distinct close days', number(stats.distinct_close_days, 0), 'days');
    field(box, 'MDD', percent(stats.mdd_pct), 'mdd');
    var sum = node('p', 'sum of trade % (not a return): ' + percent(stats.sum_trade_pct), 'asc-muted');
    box.append(sum);
    box.append(node('p', 'PF / W / L basis: ' + (stats.wins_basis || 'unverified') +
      '. ' + (stats.cost_scenario_note || 'Execution costs unverified.') +
      ' Health describes the snapshot, not a live quote or a successful database API.', 'asc-muted'));
    if (stats.limitations) {
      var limitation = node('details');
      limitation.append(node('summary', 'Evidence limitations'), node('p', stats.limitations));
      box.append(limitation);
    }
    var reasons = stats.exclusion_reasons || {};
    box.append(node('p', number(stats.excluded_n, 0) + ' excluded: ' + (Object.keys(reasons).length ?
      Object.entries(reasons).map(function (e) { return e[0] + ' (' + e[1] + ')'; }).join(' / ') : 'none')));
    if (stats.warning) box.append(node('p', 'Too good to be true: re-check price paths and selection before interpreting this result.', 'asc-warning'));
    box.append(node('p', 'Data covers: ' + (stats.first_close || 'unverified') + ' to ' + (stats.last_close || 'unverified')));
    if (Array.isArray(stats.recent5) && stats.recent5.length) {
      box.append(node('h5', 'Recent 5 (actual recorded close time, UTC)'));
      var times = stats.recent5.map(function (p) { return p.closed_at; });
      if (times.length === 5 && new Set(times).size === 1) box.append(node('p', 'batch close: times unreliable', 'asc-warning'));
      stats.recent5.forEach(function (p) { box.append(node('p', p.symbol + ' | ' + percent(p.net_pct) + ' | ' + (p.closed_at || 'unverified'))); });
    }
    return box;
  }
  function strategyTable(rows) {
    var wrap = node('div', undefined, 'asc-scroll');
    var table = node('table'), thead = node('thead'), head = node('tr'), body = node('tbody');
    [['Label / strategy / direction', 'label'], ['n / distinct close days', 'days'], ['PF (95% CI)', 'pf'],
      ['PF at 2x costs', 'costs'], ['MDD', 'mdd'], ['Top-symbol share', 'concentration'], ['Forward status / score', 'label']]
      .forEach(function (v) { var th = node('th'); th.append(help(v[0], v[1])); head.append(th); });
    thead.append(head);
    rows.forEach(function (s) {
      var tr = node('tr');
      var health = effectiveHealth(s, state.verdicts);
      [s.label + ' | ' + s.asset_class + ' | ' + (s.source_system || 'unverified source') + ' / ' + s.strategy + ' | ' + (s.direction || 'unverified') +
        ' | snapshot ' + health +
        (s.warning ? ' | Too good to be true: re-check required' : ''),
        number(s.n, 0) + ' / ' + number(s.distinct_close_days, 0),
        number(s.pf) + ' ' + interval(s.pf_ci95), number(s.pf_2x_cost), percent(s.mdd_pct),
        finite(s.top_symbol_share) ? percent(s.top_symbol_share * 100) : 'unverified',
        (s.forward_status || 'unverified') + ' | ' + number(s.score)]
        .forEach(function (value) { tr.append(node('td', value)); });
      var details = node('details'), list = node('ul');
      details.append(node('summary', 'Gate results: PASS / FAIL / N/A'));
      Object.entries(s.gates || {}).forEach(function (e) {
        var gate = e[1];
        var explanation = gateExplanation(e[0]), item = node('li');
        var expandable = node('details');
        expandable.append(node('summary', e[0] + ' ' + (typeof gate === 'string' ? gate : gate.status) + ': ' + explanation[0]),
          node('p', explanation[1]),
          node('p', 'Actual evidence: ' + (gate && gate.reason ? gate.reason : 'not supplied')));
        item.append(expandable); list.append(item);
      });
      details.append(list); tr.firstChild.append(details); body.append(tr);
    });
    table.append(thead, body); wrap.append(table); return wrap;
  }
  function renderResearchSummary(data, host) {
    var section = node('section', undefined, 'asc-card');
    section.append(node('h2', 'Plain-English decision: is there a real profit engine?'),
      node('p', 'Not established yet. Some historical groups made more than they lost under assumed costs, but that is not the same as proving a safe, repeatable trading business. Missing proof is not proof that profit is impossible.'),
      node('p', 'We cannot currently verify beating the S&P 500 or buy-and-hold. That needs a dated funded account, all open-position marks and costs, plus a matched benchmark over exactly the same unseen dates. A sum of trade percentages, a high win rate or one impressive PF cannot answer it.'),
      node('p', 'Overall analogy: we are inspecting a promising race car. Checking the tyres and speedometer is useful, but it has not won a fair race until it drives the same track as the benchmark, pays for fuel, survives bad weather and repeats the result without changing the rules.'));
    var explain = node('details'), body = node('div');
    explain.append(node('summary', 'Show / hide: how close are we, and what should happen next?'));
    body.append(node('p', 'Step 1: trustworthy inputs. Step 2: a realistic replay. Step 3: fair statistical and passive-market comparisons. Step 4: a sealed future paper test. Step 5: operator review. We are still repairing steps 1 and 2 while collecting step 4; no percentage-complete readiness score is honest.'),
      node('p', 'PASS means this specific check has evidence. FAIL means the requirement was not met. N/A means the needed evidence is missing or cannot be evaluated. Ten easy PASS results cannot cancel a failed price-path or leakage gate.'),
      node('p', 'Do not go back to generating hundreds of variants yet. First reproduce the best simple leads with correct prices, sessions and complete outcomes. If their advantage disappears after those repairs, then preregister a different strategy. Merely expanding the symbol list multiplies chances to find a lucky-looking subgroup.'),
      node('p', 'A stop and target define the experiment, not its success probability. The two-day paper monitor is a short-horizon test; a monthly ETF allocation or multi-year fund-holdings study is a different hypothesis and requires a different benchmark and cost model.'));
    explain.append(body); section.append(explain);
    var diagnostics = data.strategies.filter(function (s) {
      return s.n >= 20 && finite(s.pf) && Array.isArray(s.pf_ci95) && finite(s.pf_ci95[0]);
    }).sort(function (a,b) { return b.pf_ci95[0]-a.pf_ci95[0] || b.n-a.n || String(a.strategy).localeCompare(String(b.strategy)); }).slice(0,5);
    var detail = node('details');
    detail.append(node('summary', 'Show / hide: five historical leads worth checking, NOT verified picks'));
    detail.append(node('p', 'Diagnostic ranking only: at least 20 retained trades, then the lower end of the scenario-PF interval. This searches the same history, so selection bias remains. It is deliberately separate from Top verified picks: a FAIL row is not silently renamed CANDIDATE.'));
    diagnostics.forEach(function (s) {
      var article = node('article', undefined, 'asc-card');
      article.append(node('h3', s.asset_class + ' | ' + s.strategy + ' | ' + s.direction + ' | ' + s.label),
        node('p', 'Why investigate: ' + s.n + ' retained observations on ' + s.distinct_close_days +
          ' closing days; scenario PF ' + number(s.pf) + ', with interval ' + interval(s.pf_ci95) +
          '. This ranks conditional historical support, not expected future return. Source: ' + (s.source_system || 'unverified') + '.'));
      var name = String(s.strategy).toLowerCase();
      var concept = /breakout|donchian/.test(name) ?
        'Name-level concept only: a breakout rule asks whether price strength can persist. Analogy: checking whether a runner accelerating past a line keeps going. The strategy name does not authenticate its actual features or prove the effect.' :
        /momentum|trend|adx/.test(name) ?
        'Name-level concept only: trend/momentum rules ask whether a directional move persists. Analogy: a rolling ball sometimes keeps rolling, but friction and reversals matter. Actual causal features still need source review.' :
        'The name alone does not provide a defensible economic reason. Inspect the actual causal inputs and source thesis before assuming this is a momentum, fundamental or risk-management edge.';
      article.append(node('p', concept));
      var groups = {PASS:[],FAIL:[],'N/A':[]};
      Object.entries(s.gates || {}).forEach(function (e) {
        var status=typeof e[1] === 'string'?e[1]:e[1].status;
        if(groups[status]) groups[status].push(e[0]+' '+gateExplanation(e[0])[0]);
      });
      Object.entries(groups).forEach(function (e) { article.append(node('p', e[0]+': '+(e[1].join('; ')||'none'))); });
      article.append(node('p', 'Next action: verify original observation and entry, independently replay first-touch exits, then use a frozen unseen paper cohort. Direction is historical, not a current buy/sell call. No predicted price or calibrated certainty is established.'));
      detail.append(article);
    });
    if (!diagnostics.length) detail.append(node('p', 'No historical group meets even this descriptive minimum. Repair or collect data before selecting a lead.'));
    section.append(detail); host.append(section);
  }
  function renderTop(data) {
    var host = document.getElementById('top-verified-picks');
    if (!host) return;
    host.replaceChildren(node('h2', 'Top verified picks'), help('What do these labels mean?', 'label'));
    if (effectiveHealth({health:'OK'}, data) !== 'OK') {
      host.append(node('p', 'STALE or invalid evidence snapshot: no current MONEY-READY determination.', 'asc-warning'),
        node('p', coverage(data)));
      return;
    }
    if (!data.top_verified.some(function (s) { return s.label === 'MONEY-READY'; })) host.append(node('p', 'No MONEY-READY strategy yet', 'asc-warning'));
    if (!data.top_verified.length) host.append(node('p', 'No strategy satisfies the published CANDIDATE gates in this snapshot. No fallback list.'));
    else host.append(strategyTable(data.top_verified));
    host.append(node('p', coverage(data)), node('p', 'Rules SHA-256: ' + data.rules_hash + ' | snapshot ' + data.generated_at, 'asc-muted'));
    var research = node('details');
    research.append(node('summary', 'All scored strategies, including FAIL and missing evidence'), strategyTable(data.strategies));
    host.append(research);
    renderResearchSummary(data, host);
  }
  function renderCalls(snapshot) {
    var host = document.getElementById('audit-exit-plans');
    if (!host) return;
    host.replaceChildren(node('h2', 'Open observations: direction, exit rules and holding deadline'),
      node('p', 'Research records only, not a purchase list. A stored target is not a predicted price. No calibrated certainty is available. Missing exit or horizon rules mean no executable plan.'),
      help('TP / SL explained', 'exits'), help('Holding period explained', 'horizon'), help('Certainty explained', 'certainty'));
    var picks = (snapshot && snapshot.picks && snapshot.picks.active) || [];
    picks.forEach(function (p) {
      var plan = pickPlan(p), box = node('article', undefined, 'asc-card');
      box.append(node('h3', p.symbol + ' | ' + plan.direction + ' | research observation'));
      box.append(node('p', (p.source_system || 'unverified source') + ' / ' + (p.strategy || 'unverified strategy')));
      field(box, 'Signal observed UTC', plan.signal_at || 'unverified');
      field(box, 'Stored entry / TP / SL', number(plan.entry, 6) + ' / ' + number(plan.tp, 6) + ' / ' + number(plan.sl, 6), 'exits');
      field(box, 'Gross target / stop distance / reward:risk', percent(plan.reward_pct) + ' / ' + percent(plan.risk_pct) + ' / ' + number(plan.reward_risk), 'payoff');
      field(box, 'Holding limit', plan.horizon, 'horizon');
      field(box, 'Source bar timeframe (not holding limit)', String(p.trade_timeframe || 'unverified'));
      box.append(node('p', plan.geometry ? 'Exit geometry valid; market fill, timing and strategy evidence remain unverified.' : 'Invalid or incomplete exit geometry: no executable plan.', plan.geometry ? 'asc-muted' : 'asc-warning'));
      if (plan.signal_at && Date.now() - Date.parse(plan.signal_at) > 86400000) box.append(node('p', 'STALE signal (>24h); this is not a fresh entry.', 'asc-warning'));
      var thesis = String(p.reason || p.notes || '').trim();
      box.append(node('p', 'Source thesis (not independently verified): ' + (thesis || 'not supplied; do not infer a fundamental or technical thesis from the strategy name.')));
      host.append(box);
    });
    if (!picks.length) host.append(node('p', 'No open observations in the dashboard snapshot.'));
  }
  function unavailable() {
    ['top-verified-picks', 'crypto-panel', 'non-crypto-panel', 'owned-scorecard'].forEach(function (id) {
      var host = document.getElementById(id);
      if (host) host.replaceChildren(node('p', 'verdicts unavailable - no verified performance claim', 'asc-warning'));
    });
  }
  function renderPanels(snapshot) {
    if (snapshot) renderCalls(snapshot);
    if (!state.verdicts) { unavailable(); return; }
    try { validate(state.verdicts, snapshot); } catch (error) {
      console.warn('[Audit scorecard] Snapshot/contract validation failed');
      unavailable(); return;
    }
    renderTop(state.verdicts);
    var crypto = document.getElementById('crypto-panel'), nc = document.getElementById('non-crypto-panel');
    if (crypto) crypto.replaceChildren(card(state.verdicts.classes.CRYPTO || {}, 'Crypto'));
    if (nc) {
      nc.replaceChildren(node('h3', 'Non-Crypto - same exclusions, no strategy-deletion toggle'));
      var grid = node('div', undefined, 'asc-grid');
      Object.entries(state.verdicts.classes).filter(function (e) { return !['CRYPTO', 'NON_CRYPTO'].includes(e[0]); })
        .forEach(function (e) { grid.append(card(e[1], e[0])); });
      if (state.verdicts.classes.NON_CRYPTO) nc.append(card(state.verdicts.classes.NON_CRYPTO, 'Non-Crypto aggregate'));
      nc.append(grid);
    }
    var owned = document.getElementById('owned-scorecard');
    if (owned) {
      owned.replaceChildren(node('h2', 'Common GROK scorecard: owned strategies'),
        node('p', 'The frozen paper experiment below is separate from this closed-pick scorecard. Its preliminary experiment result never overrides these evidence gates.'),
        node('p', 'Snapshot ' + state.verdicts.generated_at + ' | ' +
          effectiveHealth({health:'OK'}, state.verdicts) + '. Historical measurements are not a current trading call.'),
        strategyTable(filterOwned(state.verdicts.strategies, JSON.parse(owned.dataset.keys || '[]'))));
      renderResearchSummary(state.verdicts, owned);
    }
  }
  async function load(snapshot) {
    if (!state.loading) state.loading = (async function () {
      try {
        var response = await fetch('data/verdicts.json', { cache: 'no-store' });
        if (!response.ok) throw new Error('Verdicts HTTP ' + response.status);
        state.verdicts = validate(await response.json());
      } catch (error) {
        state.error = 'Verdicts unavailable';
        console.warn('[Audit scorecard] Verdicts unavailable; performance claims withheld');
      }
    })();
    await state.loading;
    renderPanels(snapshot || window.DASHBOARD_DATA);
  }
  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
      var style = node('style', '.asc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.asc-card,#top-verified-picks,#audit-exit-plans,#owned-scorecard{padding:16px;margin:12px 0;background:#111a2e;color:#e2e8f0;border:1px solid #334155;border-radius:10px;overflow-wrap:anywhere}.asc-field{display:flex;justify-content:space-between;gap:12px;margin:8px 0}.asc-field strong{text-align:right}.asc-help summary{cursor:pointer;color:#7dd3fc}.asc-help p{max-width:48em;font-weight:normal;font-size:13px}.asc-muted{color:#a5b4cc;font-size:12px}.asc-warning{color:#fda4af}.asc-scroll{overflow-x:auto}.asc-scroll table{border-collapse:collapse;width:100%;min-width:800px}.asc-scroll td,.asc-scroll th{padding:10px;border-bottom:1px solid #334155;text-align:left;vertical-align:top}');
      document.head.append(style);
      load();
    });
    document.addEventListener('dashboard-data-loaded', function () { load(window.DASHBOARD_DATA); });
  }
  return { validate: validate, pickPlan: pickPlan, effectiveHealth: effectiveHealth, filterOwned: filterOwned, gateExplanation: gateExplanation, renderPanels: renderPanels, load: load, number: number, interval: interval };
});
