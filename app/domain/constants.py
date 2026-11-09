QUEUES: tuple[str, ...] = tuple(f"{group}.{sub}" for group in range(1, 7) for sub in range(1, 3))
"""All queues (черги): 1.1, 1.2 ... 6.2."""

MINUTES_IN_DAY = 24 * 60
