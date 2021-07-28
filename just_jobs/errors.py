class NotReadyException(Exception):
    def __init__(self):
        super().__init__(
            "The job manager must initialized before jobs can be enqueued."
        )


class InvalidQueueException(Exception):
    def __init__(self):
        super().__init__("The queue provided is not registered with the Manager.")
