## Summary
- what changed?
- why?

## Architecture impact
- which layer changed?
  - producer
  - ingress
  - committer
  - journal
  - view / materializer
  - agent / read-model
- did this increase or reduce coupling?

## Test plan
- [ ] `./tests/run_all.sh`
- [ ] manually tested user-facing macOS behavior if relevant
- [ ] no producer was given unnecessary read access
- [ ] no change made `notes.txt` canonical

## Notes
- follow-up work:
- rollout or migration concerns:
