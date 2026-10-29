# CareLoop walkthrough

Start with `python3 -m careloop demo --html .runs/demo.html`. This creates a
fresh synthetic scenario, executes it, and prints the actual result. Open the
HTML artifact to inspect evidence and export JSON.

## Work with the CLI

```sh
# Use a fresh local database for the one-time seed.
python3 -m careloop seed
python3 -m careloop propose DEMO-001 > proposal.json
python3 -m careloop approve proposal.json demo-reviewer 2030-01-01T10:00:00Z route-001
python3 -m careloop command DEMO-001 accept '{}' demo-owner 2030-01-01T11:00:00Z accept-001 --version 1
python3 -m careloop worklist 2030-01-04T12:00:00Z
python3 -m careloop export
```

`schedule` requires `{"slot":"timezone-aware timestamp"}` and a future slot.
`complete` requires `{"receipt":"DEMO-RECEIPT-..."}` and cannot precede the slot.
`close` requires that exact stored receipt. `decline` from routed returns a
referral to new and releases capacity. All clocks are explicit fictional inputs.
Overdue flags mark administrative elapsed time, not clinical risk.

## Reproduce and inspect

```sh
python3 -m careloop demo > demo.json
python3 -m unittest discover -s tests -v
```

`examples/demo.json` was captured from this implementation. Identifiers and
labels are synthetic. AgentBench timings vary with hardware and scheduling;
suite identity and policy outcomes remain reproducible.

## Expected failures

Invalid domain operations print a JSON error to stderr and exit 2. AgentBench's
regression gate exits 1 when a scenario regresses. Tests exercise invalid actions
and verify rejected or rolled-back state changes. No test needs external
credentials or a live model.
