from threading import Timer

class DebounceHandler:
    def __init__(self, delay):
        self.delay = delay
        self.timer = None
        self.queued_files = set()

    def debounce(self, func, file_path):
        self.queued_files.add(file_path)

        def debounced_func():
            files_to_process = self.queued_files.copy()
            self.queued_files.clear()
            for file in files_to_process:
                func(file)

        if self.timer is not None:
            self.timer.cancel()
        self.timer = Timer(self.delay, debounced_func)
        self.timer.start()
