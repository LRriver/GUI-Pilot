# Regression Notes

These notes summarize lessons from online and local GUI task logs. The original raw logs are not required at runtime.

## Stable Review Completion

For e-commerce review tasks such as JD/Pinduoduo-style flows, a strong invariant was:

```text
enter review flow -> focus text area -> TYPE review text -> COMPLETE
```

Broad post-`TYPE` VLM fallback often caused extra clicks after the task was already complete. `lite` therefore has a narrow text-completion guard.

## Explicit Submit After Text

For comment tasks that explicitly ask to publish/send/submit, the agent must not complete immediately after `TYPE`. It should click the visible send/submit region. This motivated the submit guard and the implicit submit classifier.

## Workflow Priors

Stable task families included:

- video search, playback, favorite, and comment
- map voice-pack and taxi flows
- food ordering up to checkout readiness
- flight form filling and result opening
- review/comment text entry

The design keeps these as narrow workflow priors instead of broad screen-position rules.

## Failed Heavy-Chain Lessons

Earlier heavy chains with broad critic/reflection behavior sometimes degraded online performance. The useful parts were planning, candidate review, and traceability; the risky parts were over-broad correction rules and self-evaluation state pollution. The `deep` profile keeps the useful structure while leaving `lite` as the stable default.
