# Evaluation Report

The repository includes a 100-question gold-set smoke harness.

The `/v1/trust` endpoint intentionally exposes demo fixture values so the dashboard can be demonstrated before a real benchmark pipeline exists.

**Do not present these fixture values as measured scientific results.**

For the real SIH submission:
- run the gold set against the actual model/data stack;
- record accuracy by language;
- measure TTFT and p95 latency;
- verify rainfall nowcast against ground truth;
- record alert delivery latency;
- replace fixture values with measured CI artifacts.
