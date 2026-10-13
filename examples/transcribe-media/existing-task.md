# Existing task example

## Request

```text
Use $transcribe-media to check req_0123456789abcdef0123456789abcdef and return its result if it is ready.
```

## Expected behavior

- Query the supplied task ID without creating a new task.
- If the task is pending, respect `retry_after` and use bounded polling.
- If the task succeeded and `result_available` is true, fetch the result.
- If the task failed, report its error and preserve the task ID without resubmitting.
- If the task belongs to another environment or account, report `request_not_found` without guessing.
