"""
Logger class for directing stdout to .txt log files

Author: Yakir Havin
"""


import os
import sys
from datetime import datetime


class Logger:
    def __init__(self):
        if not os.path.exists("logs"):
            os.makedirs("logs")

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%z")
        filename = os.path.join("logs", f"log_{self.timestamp}.txt")

        self.log = open(filename, "w")
        self.terminal = sys.stdout

    def write(self, message, print_to_terminal=True):
        if print_to_terminal:
            self.terminal.write(message)
            self.terminal.flush()
        self.log.write(message)
        self.log.flush()

    def flush(self):
        pass

    def close(self):
        self.log.close()


logger = Logger()
sys.stdout = logger
sys.stderr = logger