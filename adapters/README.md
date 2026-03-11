# Adapters

Optional external integrations live here.

Adapters should stay outside the core kernel logic and implement the worker interface:

- `submit_job(payload)`
- `job_status(job_id)`
- `job_result(job_id)`
