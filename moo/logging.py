import logging


class CeleryTaskFilter(logging.Filter):
    def filter(self, record):
        return record.processName.find("Worker") != -1


class CeleryProcessFilter(logging.Filter):
    def filter(self, record):
        return record.processName == "MainProcess"


class NotCeleryFilter(logging.Filter):
    def filter(self, record):
        return record.processName != "MainProcess" and record.processName.find("Worker") == -1
