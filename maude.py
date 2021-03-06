# coding = utf-8
import subprocess
import os
import tempfile
import time
from subprocess import Popen, PIPE


# input: string
# output: string without \n
# erase every occurency of the character \n on a string
def eraseLineJump(string):
    new = ""
    for i in string:
        if i != '\n' and (not string[i].isspace() or (string[i].isspace() and not string[i+1].isspace())):
            new += i
    return new


def eraseMaudeSpaces(string):
    new = ""
    i = 0
    n = len(string)
    while i < n-1:
        if not string[i].isspace() or (string[i].isspace() and not string[i+1].isspace()):
            new += string[i]
        i += 1
    return new


def eraseLineAndWarning(warnings):
    new = ""
    newWarnings = []
    for i in warnings:
        index = i.find("line")
        new = i[index:]
        index = new.find(":")
        new = new[index:]
        fIndex = new.find(".")
        new = new[:fIndex]
        newWarnings.append(new)
    return newWarnings


# input: string with warnings inside
# output: list of warnings obtained from the input string
def getWarnings(string):
    index = string.find("Warning")
    new = ""
    warnings = []
    fIndex = 0
    while index != -1 and fIndex != -1:
        new = string[index+7:]
        fIndex = new.find("Warning")
        if fIndex != -1:
            warnings.append(string[index:fIndex+6])
            string = string[fIndex:]
            index = string.find("Warning")
    warnings.append(string[index:fIndex])
    warnings = eraseLineAndWarning(warnings)
    return warnings


# Class that represents a Maude process.
# Attributes:
# p: the Maude process
# f: the output file of the Maude process
# t: time for sleep in seconds
# output: the output of the last input
# Methods:
# run(command): send the command to 'p', wait in 'f' for the answer and stores
#   the answer in 'output'.
# getOutput(): return a list with the status of the last execution,
#   the result and the complete output of the process. example:
# ["error",["Warning: ...","Warning: ..."],"Maude> red in ..."]
# ["ok","result in NTCC-RUN : < tell(..."]
class MaudeProcess:
    def __init__(self):
        self.output = ""
        self.t = 0.01
        self.timeout = 700
        # define f as a temporal file
        self.f = tempfile.TemporaryFile()
        # start Maude process, redirect stdout and stderr to f
        self.p = subprocess.Popen(
            ["(cat) | ../sccp/maude.linux64"],
            stdout=self.f,
            stderr=subprocess.STDOUT,
            stdin=PIPE,
            shell=True,
            bufsize=0
        )

    def renewProcess(self):
        processId = str(self.p.pid)
        os.system("kill -9 "+processId)
        self.p = subprocess.Popen(
            ["(cat) | ../sccp/maude.linux64"],
            stdout=self.f,
            stderr=subprocess.STDOUT,
            stdin=PIPE,
            shell=True,
            bufsize=0
        )

    def run(self, command):
        # send the command to the Maude process p
        self.p.stdin.write(command)
        self.f.seek(0)
        # read the output file of the Maude process
        r = self.f.read()
        # wait the output of the process, if is successful or have warnings
        i = 0
        while (i < self.timeout and not ("result" in r or "Warning" in r)):
            time.sleep(self.t)
            self.f.seek(0)
            r = self.f.read()
            i += 1
        self.f.seek(0)
        # erase the content of the output file
        self.f.truncate()
        if i == self.timeout:
            self.renewProcess()
            self.output = "timeout"
        else:
            # store the output r in the attribute output
            self.output = r

    def getOutput(self):
        if self.output == "timeout":
            status = "error"
            result = ["timeout"]
        else:
            index = self.output.find("result")
            if index == -1:
                index = self.output.find("Warning")
                result = self.output[index:]
                fIndex = result.find("Maude")
                result = getWarnings(result[:fIndex])
                status = "error"
            else:
                result = self.output[index:]
                fIndex = result.find("Maude")
                result = eraseMaudeSpaces(result[:fIndex])
                status = "ok"
        return [status, result, self.output]
