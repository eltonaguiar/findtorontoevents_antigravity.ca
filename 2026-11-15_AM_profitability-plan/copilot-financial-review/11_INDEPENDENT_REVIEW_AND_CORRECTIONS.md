# Independent review and methodological correction log

Two earlier focused reviewers read the asset/source catalogue and all24historical reports. A third reviewer checked this published-package draft and then its actual simulator.

## Package review

No critical/important finding; one wording correction. API authentication necessarily sends an Authorization credential to the authorized provider. README now states no credential was included in the question/state payload or retained in output, rather than claiming nothing was transmitted for authentication.

## Simulator review: important boundary-fee finding

Original `daily_returns` included initial fee-only NAV and terminal liquidation. Resampling those observations could omit or repeat one-time costs at arbitrary positions in short synthetic paths. The realized historical account was correct; the fixed-horizon scenario-cost interpretation was not.

Correction:

- Remove the entry fee-only observation from the regular-return sampling pool.
- Remove terminal liquidation's fee from the final sampled market return.
- Preserve actual recurring rebalance costs.
- Apply each account's entry and exit cost factors once, at every simulated horizon's endpoints; align SPY and cash treatment.
- Use that corrected paired process for scenario frequencies and CI diagnostics, not just a disclosure.

Two regression tests first failed, then passed: regular returns exclude boundary fees; zero-return paths at both1and100sessions end at exactly`0.99*0.98`, not a random count of fee events. All13tests pass.

The28,120realized NAV rows are byte-identical after correction. Frozen strategy, market prices,10-month lookback, execution lag, cost levels, family count and failure decision did not change. Risk frequencies/CI values were recomputed and replaced with corrected labeled values.

## Immutable protocol and audit trail

[08_SIMULATION_PLAN.md](./08_SIMULATION_PLAN.md) remains byte-identical to its preregistered SHA. The boundary correction is a measurement-method erratum, not a tuned new hypothesis or alpha discovery.

- Original runner SHA256: `909bb059335218be2217a37cd81b367da408ff00fe51114d4b666fa6fd5ff52e`.
- Superseded results SHA256: `7457d6d7a3fdc4a4ac4b17e395eac6697afb1c51d6757485bc7b2bc1aa7a5c68`.
- Boundary-corrected runner before CSV normalization: `0b29780f6c3e72f7c91998ae312b7139d970713cc5e5b65309c5d007aa378fe9`.
- Boundary-corrected results before CSV normalization: `c3168313b94c26b36a09ecd61d41da7c9a511b0376ea6b355cb91e655052a7a4`.
- Final runner SHA256: `c4caaf715539cdfc5c70ffd0b9da4c521d74316b01d29d15d2388b1c76b9cba8`.
- Final results SHA256: `15aafe71d12eadfad0d5a6407fcc52f44996c67a13a54e2d803d4db22c60b8ef`.

Final CSV output uses LF rather than CRLF line endings so repository whitespace checks pass. Every price and NAV value was verified byte-for-byte after normalizing old line endings; original vendor-response hashes were unchanged. This is serialization only, not a data/model revision.

The independent reviewer confirmed the specific boundary-cost finding resolved with no remaining substantive blocker; they inspected the fix/tests but did not rerun them. The parent ran all13tests and the corrected simulations.

Updated measured values and source/NAV hashes are in [SIMULATION_QA.json](./SIMULATION_QA.json). Historical observations and synthetic samples are not independent forward evidence. Capital permission remains false; H-143 remains a failed alpha screen.
