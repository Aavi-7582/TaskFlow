def execute_task(task_type, payload):
    if task_type == "fibonacci":
        n = payload["n"]

        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b

        return a

    elif task_type == "sleep":
        import time

        seconds = payload.get("seconds", 5)
        time.sleep(seconds)

        return f"Slept for {seconds} seconds"

    else:
        raise ValueError(f"Unknown task type: {task_type}")