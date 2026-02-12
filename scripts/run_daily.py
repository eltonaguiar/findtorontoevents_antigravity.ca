# run_daily.py - Run daily GROK_XAI tasks

import os

# Run HMM regime detection
os.system('python scripts/hmm_regime.py')

# Run Kelly sizing
os.system('python scripts/kelly_sizer.py')

# Run correlation pruner
os.system('python scripts/corr_pruner.py')

print('Daily tasks completed.')