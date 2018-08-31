import asyncio
import time
import subprocess as sp
from inspect import ismethoddescriptor
from .tables.scheduler import Task
from .service import status_monitor


class CrontabParser:
    """
    解析crontab格式字符串
    """
    def parse(self, string):
        minute, hour, dom, month, dow = string.split()
        minute = self.handle_unit(minute, "minute", 60)
        hour   = self.handle_unit(hour, "hour", 24)
        dom    = self.handle_unit(dom, "day", 31)
        month  = self.handle_unit(month, "month", 12)
        dow    = self.handle_unit(dow, "weekday", 7)
        func   = lambda x: minute(x) and hour(x) and dom(x) and month(x) and dow(x)
        return func

    def handle_unit(self, string, attr, maxvalue):
        per = 1
        if "/" in string:
            string, per = string.split("/")
            per = int(per)
        if minute == "*":
            if per == 1:
                return lambda x: True
            else:
                times = range(maxvalue)
        else:
            times = set()
            for t in string.split(","):
                if t.isdigit():
                    times.add(int(t))
                else:
                    ts, te = map(int, t.split("-"))
                    if te < ts:
                        t.update(set(range(ts, maxvalue)))
                        t.update(set(range(0, te+1)))
                    else:
                        t.update(set(range(ts, te+1)))
        times = [t for i, t in enumerate(sorted(times)) if i % per == 0]
        if issmethoddescriptor(getattr(datetime, attr)):
            return lambda x: getattr(x, attr)() in times
        else:
            return lambda x: getattr(x, attr) in times


class Job:
    def __init__(self):
        self.activated = False

    async def start(self):
        raise NotImplementedError

    def __bool__(self):
        return self.activated


class CommandJob(Job):
    """
    任务
    """
    def __init__(self, name, command, logfile, crontab, activated=True):
        parser = CrontabParser()
        self.name      = name
        self.command   = command
        self.logfile   = logfile
        self.crontab   = crontab
        self.activated = activated
        self.on        = parse(crontab)

    @staticmethod
    def from_task(task):
        return Job(
            job.Name,
            job.Command,
            job.LogFile,
            job.Crontab,
            job.Activated
        )

    async def start(self):
        pass


class PythonJob(Job):
    def __init__(self, name, function, args=None, kwargs=None, activated=True):
        self.name      = name
        self.function  = function
        self.args      = args or ()
        self.kwargs    = kwargs or {}
        self.activated = activated

    async def start(self):
        self.function(*self.args, **self.kwargs)


class Scheduler:
    def __init__(self):
        self.jobs = {}

    def load(self):
        for task in Task.objects:
            if task.Activated:
                job = CommandJob.from_task(task)
                self.add(job)
            else:
                self.jobs.pop(task.Name, None)

    def add(self, job):
        if job and job not in self:
            self.jobs[job.name] = job

    @status_monitor("scheduler")
    async def run(self):
        while 1:
            coros = []
            for job in self.check_jobs():
                coros.append(job.start())
            asyncio.gather(coros)
            await asyncio.sleep(60)

    def check_jobs(self):
        time = time.time()
        for job in self.jobs.values():
            if job.on(time):
                yield job

    def install_update(self):
        self.add(PythonJob("*UpdateJobs", self.load))

    def __contains__(self, job):
        return job.name in self.jobs
