class NotReadyException(Exception):
    def __init__(self):
        super().__init__("The job manager must initialized before anything can happen.")


class InvalidQueueException(ValueError):
    def __init__(self):
        super().__init__("The queue provided is not registered with the Manager.")


class InvalidEnqueueableFunction(TypeError):
    def __init__(self):
        super().__init__("You need to enqueue a callable function.")
