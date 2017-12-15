# coding=utf-8
from parse import * 
dictionary = {}
import os, sys
maudeprocess=-1
from process import *
def StoreRoot(mem):
    global dictionary
    parsingResult=parse("{}[{}]", mem )
    parsingResult[1]
    return 0

def StoreMemory(mem):
    stack=[0]
    mem=StoreRoot(mem)
    i=0
    while i < len(mem):
        if mem[i] == "[":
            stack.append(0)
            i+=1
        elif mem[i] == "]":
            stack.pop()
            i+=1
        elif mem[i] == ":" :
            stack.append(stack.pop()+1)
            i+=1
        elif mem[i:i+12] == "empty-forest":
            i+=12
        else:
            i+=StoreChildren(mem,stack)
            
def initMaude():
    global maudeprocess
    ##os.system("killall maude.linux64")
    maudeprocess=int(os.popen("(cat) | ./Maude/maude.linux64 > outputimportant.txt 2>&1 & echo $!").read())
    print maudeprocess
    
def runMaude(command):
    global maudeprocess
    os.system("echo '"+command+"' > /proc/"+str(maudeprocess)+"/fd/0")


def auxextract(filename):
    v1=os.popen("cp "+filename+" isee.txt").read()
    file=open("isee.txt","r")
    notfound=True
    r1=file.readline()
    print r1
    while r1 == "" :
        print "una vez2"
        v1=os.popen("cp "+filename+" isee.txt").read()
    file=open("isee.txt","r")
    notfound=True
    r1=""
    # while(notfound and not("Bye." in r1) ):
    #     print "una vez"
    #     r1=file.readline()
    #     print r1
    #     if "result" in r1:
    #         notfound=False
    #         print r1
    #     elif "Warning" in r1:
    #         os.system("cat /dev/null > outputimportant.txt")
    #         file.close()
    #         print "error"

def extractInfo(filename):
    file=open(filename,"r")
    notfound=True
    r1=""
    while(notfound and not("Bye." in r1) ):
        print "una vez"
        r1=file.readline()
        print r1
        if "result" in r1:
            notfound=False
        elif "Warning" in r1:
            ##os.system("cat /dev/null > outputimportant.txt")
            file.close()
            return "error"
    if(notfound):
        ##os.system("cat /dev/null > outputimportant.txt")
        file.close()
        return "error"
    else:
        resultvar=r1
        notend=True
        while(notend):
            r1=file.readline()
            if "Bye." in r1:
                notend=False
            else:
                resultvar= resultvar + r1[3:]
        resultvar=erraseLineJump(resultvar)
        if(resultvar[0]=="r"):
            ##saveState(resultvar)
            ##ntccTictac(ntcctime)
            ##os.system("cat /dev/null > outputimportant.txt")
            file.close()
            return resultvar
            
def erraseMaudeSpaces(string):
    new=""
    i=0
    n=len(string)
    while i < n-1:
        if not string[i].isspace() or (string[i].isspace() and not string[i+1].isspace()):
            new+=string[i]
        i+=1
    return new
    
# initMaude()
# command='red in NTCC-RUN : IO(< tell("bla") || tell("hello world") ; empty[empty-forest] >) .'
# runMaude(command)
# auxextract("outputimportant.txt")
# ##print extractInfo("outputimportant.txt")
# command2='red in NTCC-RUN : IO(< tell("hehehe") || tell("blablabla") ; empty[empty-forest] >) .'
# runMaude(command2)
# ##print extractInfo("outputimportant.txt")
# m=MaudeProcess()
# print m
cadena="blabla  bla  \n bla bbla  bla  \n   (!)as  sd   ."
print "cadena antes de : " + cadena
print "despues : " + erraseMaudeSpaces(cadena)
