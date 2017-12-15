# coding=utf-8
import subprocess
import tempfile
import time
from subprocess import Popen, PIPE

def erraseLineJump(string):
    new=""
    for i in string:
        if i != '\n':
            new+=i
    return new
    
def getWarnings(string):
    index=string.find("Warning")
    new=""
    warnings=[]
    findex=0
    while index!=-1 and findex!=-1:
        new=string[index+7:]
        findex=new.find("Warning")
        if findex != -1:
            warnings.append(string[index:findex+6])
            string=string[findex:]
            index=string.find("Warning")
    warnings.append(string[index:findex])
    return warnings
    
class MaudeProcess:
    def __init__(self):
        self.output=""
        self.t=0.01
        self.f = tempfile.TemporaryFile() 
        # start process, redirect stdout
        self.p = subprocess.Popen(["(cat) | ./Maude/maude.linux64"],
                         stdout=self.f,
                         stderr=subprocess.STDOUT,
                         stdin=PIPE,
                         shell=True,
                         bufsize=0)
    def run(self,command):
        self.p.stdin.write(command)
        self.f.seek(0) 
        r=self.f.read()
        while (not ("result" in r or "Warning" in r)):
            time.sleep(self.t)
            self.f.seek(0)
            r=self.f.read()
        self.f.seek(0)
        self.f.truncate()
        self.output=r
    def extractInfo(self):
        index=self.output.find("result")
        if index==-1:
            index=self.output.find("Warning")
            result=self.output[index:]
            findex=result.find("Maude")
            result=getWarnings(result[:findex])
            status="error"
        else:
            result=self.output[index:]
            findex=result.find("Maude")
            result=erraseLineJump(result[:findex])
            status="ok"
        return [status,result]
        