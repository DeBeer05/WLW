from unittest import TextTestResult
from unittest.result import TestResult

from django.test.runner import DiscoverRunner


class RedStatusTextTestResult(TextTestResult):
    GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"

    def _write_status(self, color, verbose_text, dot_text):
        if self.showAll:
            self.stream.writeln(f"{color}{verbose_text}{self.RESET}")
        elif self.dots:
            self.stream.write(f"{color}{dot_text}{self.RESET}")
            self.stream.flush()

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        self._write_status(self.GREEN, "PASSED", ".")

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        self._write_status(self.RED, "ERROR", "E")

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        self._write_status(self.RED, "FAIL", "F")

    def addExpectedFailure(self, test, err):
        TestResult.addExpectedFailure(self, test, err)
        self._write_status(self.RED, "expected failure", "x")

    def addUnexpectedSuccess(self, test):
        TestResult.addUnexpectedSuccess(self, test)
        self._write_status(self.RED, "unexpected success", "u")


class RedStatusDiscoverRunner(DiscoverRunner):
    def get_test_runner_kwargs(self):
        kwargs = super().get_test_runner_kwargs()
        kwargs["resultclass"] = RedStatusTextTestResult
        kwargs["verbosity"] = max(kwargs.get("verbosity", 1), 2)
        return kwargs