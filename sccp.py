from flask import Flask, jsonify, request
from parse import *
from maude import *
from crontab import CronTab

##Structure of messages: "<clock,id_user>message"
##System files are located inside the following directory
systemfiles="~systemfiles/"

#This function get the ntcc time counter, it's stored in a txt file
def getNtccTime():
    cl=open(systemfiles+"ntcctime.txt","r")
    time=cl.readline()
    cl.close()
    return int(time)
maude=MaudeProcess()

##Definition of some global variables
nameinput=systemfiles+"run.txt"
nameoutput=systemfiles+"output.txt"
namememory=systemfiles+"memory.txt"
nameprocess=systemfiles+"process.txt"
memory=""
processes=""
ntcctime=getNtccTime()
memoryDicc={}
notbussy=True
##Function that obtains every message inside a string of messages from the memory of an agent
##stringMessages: '"message 1", "message 2", "message 3" ... '
##return: ['message 1', 'message 2', 'message 3' ...]
def splitMessages(stringMessages):
    messages=[]
    message=""
    quotecounter=0
    for c in stringMessages:
        if c=='"':
            quotecounter+=1
        elif c=="," and quotecounter%2 == 0:
            messages.append(message)
            message=""
        elif quotecounter%2 != 0:
            message=message+c
    messages.append(message)
    return messages

def storeChild(memory,stack,i):
    global memoryDicc
    path = str(stack[0])
    for j in stack[1:]:
        path=path+"."+str(j)
    agentString=memory[i:]
    index=agentString.find("[")
    if index!= -1:
        agentString=agentString[:index]
        messages=splitMessages(agentString)
        memoryDicc[path] = messages
    return index

def storeMemory(mem) :
    stack=[0]
    i=storeChild(mem,stack,0)
    while i < len(mem) :
        if mem[i] == "[" :
            stack.append(0)
            i+=1
        elif mem[i] == "]" :
            stack.pop()
            i+=1
        elif mem[i] == ":" :
            stack.append(stack.pop()+1)
            i+=1
        elif mem[i:i+12]=="empty-forest":
            i+=12
        elif mem[i] == " ":
            i+=1
        else:
            i+=storeChild(mem,stack,i)

def getClocks():
    global memoryDicc
    base="0."
    i=0
    space=base+str(i)
    clocks=[]
    while memoryDicc.get(space) != None:
        i+=1
        clocks.append(memoryDicc.get(space+".6"))
        space=base+str(i)
    return clocks

def getNotifications():
    global memoryDicc
    base="0."
    i=0
    space=base+str(i)
    notifications=[]
    while memoryDicc.get(space) != None:
        i+=1
        notifications.append(memoryDicc.get(space+".10"))
        space=base+str(i)
    return notifications

def storeNotifications(notifications):
    return 0


##Function that errase spaces from a program,
##that are after every ocurrency of the searchingString
##input:
##program -> is the input program,
##searchingString -> the string that the function will search
##for erasing the spaces after it
def erraseSpacePostAndSay(program,searchingString):
    index=program.find(searchingString)
    oldindex=0
    while index != -1 :
        index=index+oldindex+4
        while program[index] == " ":
            program=program[:index] + program[index+1:]
        oldindex=index
        index=program[index:].find(searchingString)
    return program

##Function for adding the program id to a new process
##input: program -> process without tags
##output: program -> process tagged, changging
##<pid| with the pid of this time unit
def addPid(program):
  global ntcctime
  pidstr='<pid|'
  index=program.find(pidstr)
  oldindex=0
  while index!=-1:
      index=oldindex+index+1
      pid=str(ntcctime)
      program=program[:index]+pid+program[index+3:]
      oldindex=index+len(pid)
      index=program[oldindex:].find(pidstr)
  return program

##Function for adding the user to a new process
##input:
##program -> process without tags
##user -> the user that will be added to the process
##output: program -> process tagged, changging
##<usn| with the username in the input
def addUser(program,user):
  userstr='|usn>'
  index=program.find(userstr)
  oldindex=0
  while index!=-1:
      index=oldindex+index+1
      program=program[:index]+user+program[index+3:]
      oldindex=index+len(user)
      index=program[oldindex:].find(userstr)
  return program


##Function for adding the program id to a new process
##input: program -> process without tags
##output: program -> process tagged, changing
##{pid} with the pid of this time unit
def addPidPosted(program):
  global ntcctime
  pidstr='{pid}'
  index=program.find(pidstr)
  oldindex=0
  while index!=-1:
      index=oldindex+index
      pid=str(ntcctime)
      program=program[:index]+pid+program[index+5:]
      oldindex=index+len(pid)
      index=program[oldindex:].find(pidstr)
  return program

##Function that increase the ntcc time counter
def ntccTictac(c):
    cl=open(systemfiles+"ntcctime.txt","w")
    stwrite=str(c+1)
    cl.write(stwrite)
    cl.close()

##Function for adding the program id and user to every post in a process
##input: program -> process without tags
##input: id_user -> username of the user who post the process
##output: program -> process tagged, adding clock and username
##to the messages
def addIdandOrder(program,id_user):
  tellstr='post("'
  index=program.find(tellstr)
  oldindex=0
  while index!=-1:
      index=oldindex+index+6
      userstr="<pids|p|" +str(id_user)+">"
      program=program[:index]+userstr+program[index:]
      oldindex=index+len(userstr)
      index=program[oldindex:].find(tellstr)
  program=addIdandOrderSignal(program,id_user)
  return program

##Function for adding the program id and user to every post in a process
##input: program -> process without tags
##input: id_user -> username of the user who post the process
##output: program -> process tagged, adding clock and username
##to the messages
def addTagVote(program,id_user):
  tellstr='vote("'
  index=program.find(tellstr)
  oldindex=0
  while index!=-1:
      index=oldindex+index+6
      userstr="<pids|v|" +str(id_user)+">"
      program=program[:index]+userstr+program[index:]
      oldindex=index+len(userstr)
      index=program[oldindex:].find(tellstr)
  program=addIdandOrderSignal(program,id_user)
  return program

##Function for adding the program id and user to every say in a process
##input: program -> process without tags
##input: id_user -> username of the user who post the process
##output: program -> process tagged, adding clock and username
##to the messages
def addIdandOrderSignal(program,id_user):
  global ntcctime
  tellstr='signal("'
  index=program.find(tellstr)
  oldindex=0
  ntcctime=getNtccTime()
  while index!=-1:
      index=oldindex+index+8
      userstr="<pids|s|" +str(id_user)+">"
      program=program[:index]+userstr+program[index:]
      oldindex=index+len(userstr)
      index=program[oldindex:].find(tellstr)
  return program

##Function for adding the program id and user to every say in a process
##input: program -> process without tags
##input: id_user -> username of the user who post the process
##output: program -> process tagged, adding clock and username
##to the messages
def addIdandOrderSay(program,id_user):
  global ntcctime
  tellstr='say("'
  index=program.find(tellstr)
  oldindex=0
  ntcctime=getNtccTime()
  while index!=-1:
      index=oldindex+index+5
      userstr="<pid|s|" +str(id_user)+">"
      program=program[:index]+userstr+program[index:]
      oldindex=index+len(userstr)
      index=program[oldindex:].find(tellstr)
  program=addIdandOrderSignal(program,id_user)
  return program

##Function that extract the information of a string that contains a message
def extractInfo(msg):
    global ntcctime
    clock=ntcctime
    parseResult=parse('<{}>{}',msg)
    if parseResult is None :
        if msg.find("{pid") == -1:
            r={'clock' : clock , 'user_msg' : "private" , 'msg' : msg , 'class' : "system" }
        else:
            msg=msg.replace("{","[")
            msg=msg.replace("}","]")
            r={'clock' : clock , 'user_msg' : "private" , 'msg' : msg , 'class' : "process" }
    else :
        info=parseResult[0]
        message=parseResult[1]
        info=info.split("|")
        r={'clock' : info[0] , 'user_msg' : info[2] , 'msg' : message , 'class' : "none" }
    return r

##Procediment that load the current state from the txt files
##to the global variables that represent the current memory and processes
def refreshState():
    global namememory
    global nameprocess
    mem = open(namememory,"r")
    proc = open(nameprocess,"r")
    global processes
    global memory
    processes = proc.readline()
    memory = mem.readline()
    mem.close()
    proc.close()

refreshState()

##Function that eliminate the first agent of the agents string
##input: agents -> string with agents
##output: agents -> string with agents, but without the first one
def elimOther(agents):
    stack=[]
    index=0
    for i in agents:
        if i!='[' :
            index+=1
        else:
            index+=1
            stack.append("[")
            break
    while index < len(agents):
        i=agents[index]
        if i=='[':
            stack.append("[")
        elif i==']':
            stack.pop(0)
        index+=1
        if len(stack)==0:
            break
    index+=3
    return agents[index:]

##Function that choose the first agent of the agents string
##input: agents -> string with agents
##output: agents -> the first agent on the string
def getCurrAgent(agents):
    stack=[]
    index=0
    for i in agents:
        if i!='[' :
            index+=1
        else:
            index+=1
            stack.append("[")
            break
    while index < len(agents):
        i=agents[index]
        if i=='[':
            stack.append("[")
        elif i==']':
            stack.pop(0)
        index+=1
        if len(stack)==0:
            break
    return agents[:index]



##Function that convert the agent memory in a json list with every message with their information
def convertMemInJson(mem):
    index=1
    dendex=1
    messages="error"
    memParse=parse("({})",mem)
    if memParse != None:
        messages=splitMessages(memParse[0])
    else:

        messages=[mem[1:len(mem)-1]]
    jMessages=[]
    for i in messages:
        jMessages.append(extractInfo(i))

    return jMessages


##Function that go through on the memory, searching the space of an agent
##input: agentId -> id of the agent that want to calculate
##output: agents -> the agent memory
def calculateAgentMemory(agentId):
    refreshState()
    parsingResult=parse("{}[{}]", memory )
    agents=parsingResult[1]

    while agentId>0:
        agents=elimOther(agents)
        agentId=agentId-1
    agents=getCurrAgent(agents)

    return agents

##Function that go through on the memory, searching the space of an agent
##input: store -> the store of the system
##input: agentId -> id of the agent that want to calculate
##output: agents -> the agent memory
def calculateAgentMemoryAlpha(store,agentId):
    parsingResult=parse("{}[{}]", store)
    agents=parsingResult[1]
    while agentId>0:
        agents=elimOther(agents)
        agentId=agentId-1
    agents=getCurrAgent(agents)
    return agents

##Function for adding the program id and user to every post in a process
##input: memory -> memory without current pid
##input: timeunit -> current timeunit
##output: memory -> memory with current pid
##on posts
def replacePidAfter(memory,timeunit):
    timeunit=str(timeunit)
    pidstr='<pids|'
    index=memory.find(pidstr)
    oldindex=0
    while index!=-1:
        index=oldindex+index+1
        memory=memory[:index]+timeunit+memory[index+4:]
        oldindex=index+len(timeunit)
        index=memory[oldindex:].find(pidstr)
    return memory

def createClock(path, timer):
    cron = CronTab(user='dspacenet')
    path=str(path)
    iter = cron.find_comment('p'+path+'$')
    for i in iter:
        cron.remove(i)
    if timer != "0":
        job = cron.new(command=' ~/.nvm/versions/node/v9.4.0/bin/node ~/dspacenet/node/helpers/tickWorker.js ' + path, comment='p'+path+'$')
        job.setall(timer)
    cron.write()

def mergeNotifications(notifications):
    global notificationsList
    for i in len(notifications):
        if notificationsList[i] != None:
            notificationsList[i] = notificationsList[i] + notifications[i]
        else:
            notificationsList[i] = notifications[i]

##Procediment that store a successful execution on the memory and processes txt files
def saveState(result):
    global ntcctime
    ntcctime=getNtccTime()
    global processes
    global memory
    global memoryDicc
    parsingResult=parse("result Conf: < {} ; {} >", result )
    processes=parsingResult[0]
    memory=parsingResult[1]
    memory=replacePidAfter(memory,ntcctime)
    mem=open(namememory,"w")
    mem.write(memory)
    mem.close()
    memoryDicc = {}
    storeMemory(memory)
    clocks=getClocks()
    #notifications=getNotifications()
    #mergeNotifications(notifications)
    print clocks
    i=0
    while i < len(clocks):
        if clocks[i] != None and clocks[i][0] != '':
            createClock(i, clocks[i][0])
        i+=1
    proc=open(nameprocess,"w")
    proc.write(processes)
    proc.close()

##Function that get a list of errors and convert it
##into a list of errors in json.
##input: [error1,error2,...,errorn]
##output: [{'error': error1, 'error': error2...,'errorn': errorn}]
def errorToJson(errors):
    jErrors=[]
    for i in errors:
        element={ 'error' : i }
        jErrors.append(element)
    return jErrors


##Routes of the rest server
import os
app = Flask(__name__)

##This route is for looking if the rest server is on
@app.route('/', methods=['GET'])
def index():
    return jsonify({'message' : 'SCCP'})



##This route is for running a program
##It comunicate the program to the sccp
##VM and store the result
##For using it.
##input[json]:
##{
## "config" : "here will be an input process"
## "user" : "the user who posts the process"
## "timeu" : "if the timeunit will advance, don't send anything, else, send False"
##}
##output[json]:
##{
## "result" : "it could be ok or error",
## "errors" : "if the result is error,
## here will be the maude errors"
##}
@app.route('/runsccp', methods=['POST'])
def runsccp():
    global notbussy
    notbussy=True
    if notbussy:
        global ntcctime
        ntcctime=getNtccTime()
        global processes
        global memory
        global maude
        refreshState()
        received = request.json['config']
        userp = request.json['user']
        timeunit = str(request.json['timeu'])
        if received=="":
            notbussy=True
            return jsonify({'result' : 'error', 'errors' : [{'error' : 'empty input'}]})
        received = erraseSpacePostAndSay(received,"post")
        received = erraseSpacePostAndSay(received,"say")
        received = addIdandOrder(received,userp)
        reveived = addTagVote(received,userp)
        try:
            receivedstr=str(received)
        except:
            errors=errorToJson(["characters not allowed"])
            notbussy=True
            return jsonify({'result' : 'error', 'errors' : errors })
        maude.run("red in SCCP-RUN : "+received+" . \n")
        answer=maude.getOutput()
        if answer[0]=="error":
            errors=errorToJson(answer[1])
            notbussy=True
            return jsonify({'result' : 'error', 'errors' : errors })
        else:
            parsingResult=parse("result SpaInstruc: {}", answer[1] )
            received=parsingResult[0]
        received = addPid(received)
        received = addPidPosted(received)
        received = addUser(received,userp)
        processes = received +" || " + processes
        maude.run("red in NTCC-RUN : IO(< "+processes+" ; "+memory+" >) . \n")
        answer=maude.getOutput()
        if answer[0]=="error":
            errors=errorToJson(answer[1])
            notbussy=True
            return jsonify({'result' : 'error', 'errors' : errors})
        else:
            saveState(answer[1])
            if timeunit=="1":
                ntccTictac(ntcctime)
            notbussy=True
            return jsonify({'result' : 'ok'})
    else:
        return jsonify({'result' : 'error', 'errors' : [{'error' : "bussy, try again"}]})

@app.route('/getSpace', methods=['POST'])
def getSpace():
    global memoryDicc
    agent=request.json['id']
    path="0"
    for i in agent:
        path=path+"."+str(i)
    try:
        result=memoryDicc[path]
        newResult=[]
        for i in result:
            newResult.append(extractInfo(i))
        result=newResult
    except:
        result = []
    result.sort(key=lambda clock: int(clock['clock']),reverse=True)
    return jsonify({'result' : result})

##This function returns the global memory
@app.route('/getGlobal', methods=['GET'])
def getGlobal():
    global memory
    #answer=getCurrAgent(memory)
    parsingResult=parse("{}[{}]", memory )
    if parsingResult[0] is None:

        return jsonify({'result' : 'Empty'})
    else:

        answer=convertMemInJson(parsingResult[0])
        answer.sort(key=lambda clock: int(clock['clock']),reverse=True)
        return jsonify({'result' : answer})



if __name__ == '__main__':
    app.run(host= '0.0.0.0',port=8082)


