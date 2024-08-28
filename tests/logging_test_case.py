import unittest
import sys
import logging


class LoggingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up logging to write to stdout
        cls.logger = logging.getLogger(cls.__name__)
        cls.logger.setLevel(logging.DEBUG)

        # Create a StreamHandler for stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        # Create a Formatter and set it for the handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        # Add the handler to the logger
        cls.logger.addHandler(handler)

    def setUp(self):
        self.logger.info(f"Starting test: {self._testMethodName}")

    def tearDown(self):
        self.logger.info(f"Finished test: {self._testMethodName}")

    def run(self, result=None):
        test_method = getattr(self, self._testMethodName)
        doc = test_method.__doc__
        if doc:
            self.logger.info(f"Test description: {doc.strip()}")
        super().run(result)


class MyTests(LoggingTestCase):
    def test_example(self):
        """This is an example test."""
        self.logger.debug("This is a debug message")
        self.logger.info("This is an info message")
        self.assertEqual(1 + 1, 2)
        self.logger.warning("This is a warning message")
