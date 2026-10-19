echo '=== STEP A: Inventory forward-test harness files in alpha_engine/ ==='
ls -lah alpha_engine/forward_validator.py alpha_engine/scanner.py alpha_engine/production_scanner.py 2>&1 | head -5
echo
echo '--- battleground_luxalgo strategy source ---'
find alpha_engine/ -name '*battleground*' -o -name '*luxalgo*' 2>&1 | head -20
echo
echo '--- alpha_engine/strategies/ inventory ---'
ls alpha_engine/strategies/ 2>&1 | head -30
echo
echo '--- alpha_engine/stamp / forward-test related ---'
ls alpha_engine/stamp_entry_conditions.py alpha_engine/forward_test*.py 2>&1 | head -10

echo
echo '=== STEP B: forward_test_only env var usage across the harness ==='
grep -rn 'forward_test_only\|FORWARD_TEST_ONLY\|forward_only\|FORWARD_ONLY\|paper_only\|PAPER_ONLY' alpha_engine/ tools/audit_trail/dashboard_generator.py tools/picks_now_professional.py tools/build_pf_registry.py 2>/dev/null | head -30

echo
echo '=== STEP C: forward-test manifest lookup ==='
ls -lah config/forward_test*.json config/forward*.json config/hf_conviction_tiers.json config/hc_gate_params.json 2>&1 | head -20
echo
find . -name '*forward_test*.json' -o -name 'forward_picks.json' -o -name 'forward_n_tracker.json' 2>&1 | head -10

echo
echo '=== STEP D: existing forward-write sidecars ==='
ls -lah audit_dashboard/data/forward*.json audit_dashboard/data/entry_conditions_forward.json 2>&1 | head -10
echo
ls -lah entry_conditions_forward.json 2>&1 | head -3

echo
echo '=== STEP E: forward_validator.py smoke (size + signatures + key emission logic) ==='
if [ -f alpha_engine/forward_validator.py ]; then
  wc -l alpha_engine/forward_validator.py
  echo
  grep -n 'def \|forward_test_only\|paper.*trade\|STRATEGY.*=' alpha_engine/forward_validator.py 2>&1 | head -30
fi

echo
echo '=== STEP F: stamp_entry_conditions.py + battleground_luxalgo smoke ==='
./tools/stamp_entry_conditions.py 2>&1 | head -5 || echo '  stamp_entry_conditions NOT FOUND in tools/'
echo
find . -name 'stamp_entry_conditions*' 2>&1 | head -5
echo
if [ -f alpha_engine/battleground_luxalgo.py ]; then
  wc -l alpha_engine/battleground_luxalgo.py
  grep -n 'def \|class \|emits\|paper_only\|forward' alpha_engine/battleground_luxalgo.py 2>&1 | head -20
fi
echo
echo '--- battleground_luxalgo in strategies/ ---'
ls alpha_engine/strategies/battleground_luxalgo.py alpha_engine/strategies/*luxalgo*.py 2>&1 | head -10

echo
echo '=== STEP G: forward-pilot monitor / counter (cron-compatible) ==='
find . -name 'forward*.py' -not -path '*/.*' 2>&1 | head -15
echo
find tools/ -name '*forward*' -o -name '*paper*' 2>&1 | head -15
