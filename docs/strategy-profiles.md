# Strategy Profiles

## `lite`

`lite` is the default and recommended profile.

It combines:

- workflow priors for high-confidence task families
- single VLM fallback for unknown screens
- compact action history
- text-entry and submit guards
- robust output parsing and coordinate validation

Use it when you want predictable behavior, low latency, and a small dependency surface.

## `deep`

`deep` is the high-budget profile.

It adds:

- coarse task planning
- crop-region proposals
- multiple candidate generation
- candidate review
- deterministic arbitration
- bounded reflection memory

Use it for research, debugging, and high-budget inference settings. The current implementation intentionally reuses `lite` as its execution substrate, so the deeper layers can be strengthened incrementally without breaking the stable path.
