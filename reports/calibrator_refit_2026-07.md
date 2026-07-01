# Confidence Calibrator Refit — 2026-07

Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/confidence_calibrator.py", line 289, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/confidence_calibrator.py", line 281, in main
    return _cmd_fit()
           ^^^^^^^^^^
  File "/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/alpha_engine/confidence_calibrator.py", line 239, in _cmd_fit
    with path.open("r", encoding="utf-8") as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/pathlib.py", line 1044, in open
    return io.open(self, mode, buffering, encoding, errors, newline)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/home/runner/work/findtorontoevents_antigravity.ca/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json'
