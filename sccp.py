from flask import Flask, jsonify, request
from parse import parse
from maude import MaudeProcess
from crontab import CronTab
import os

# Structure of messages: "<clock,id_user>message"
# System files are located inside the following directory
systemfiles = "~systemfiles/"


# This function get the ntcc time counter, it's stored in a txt file
def getNtccTime():
    cl = open(systemfiles+"ntcctime.txt", "r")
    time = cl.readline()
    cl.close()
    return int(time)

# Definition of some global variables
maude = MaudeProcess()
nameinput = systemfiles+"run.txt"
nameoutput = systemfiles+"output.txt"
MEMORY_FILE = systemfiles+"memory.txt"
PROCESS_FILE = systemfiles+"process.txt"
memory = ""
processes = ""
ntccTime = getNtccTime()
memoryDictionary = {}
notBusy = True


# Function that obtains every message inside a string of messages from the
# memory of an agent stringMessages: '"message 1", "message 2", "message 3" ...
# ' return: ['message 1', 'message 2', 'message 3' ...]
def splitMessages(stringMessages):
    messages = []
    message = ""
    quotecounter = 0
    for c in stringMessages:
        if c == '"':
            quotecounter += 1
        elif c == "," and quotecounter % 2 == 0:
            messages.append(message)
            message = ""
        elif quotecounter % 2 != 0:
            message = message+c
    messages.append(message)
    return messages


def storeChild(memory, stack, i):
    global memoryDictionary
    path = str(stack[0])
    for j in stack[1:]:
        path = path+"."+str(j)
    agentString = memory[i:]
    index = agentString.find("[")
    if index != -1:
        agentString = agentString[:index]
        messages = splitMessages(agentString)
        memoryDictionary[path] = messages
    return index


def storeMemory(mem):
    stack = [0]
    i = storeChild(mem, stack, 0)
    while i < len(mem):
        if mem[i] == "[":
            stack.append(0)
            i += 1
        elif mem[i] == "]":
            stack.pop()
            i += 1
        elif mem[i] == ":":
            stack.append(stack.pop()+1)
            i += 1
        elif mem[i:i+12] == "empty-forest":
            i += 12
        elif mem[i] == " ":
            i += 1
        else:
            i += storeChild(mem, stack, i)


def getClocks():
    base = "0."
    i = 0
    space = base+str(i)
    clocks = []
    while memoryDictionary.get(space) !=  None:
        i += 1
        clocks.append(memoryDictionary.get(space+".6"))
        space = base+str(i)
    return clocks


def getNotifications():
    base = "0."
    i = 0
    space = base+str(i)
    notifications = []
    while memoryDictionary.get(space) != None:
        i += 1
        notifications.append(memoryDictionary.get(space+".10"))
        space = base+str(i)
    return notifications


def storeNotifications(notifications):
    return 0


# Function that erase spaces from a program,
# that are after every occurency of the searchingString
# input:
# program -> is the input program,
# searchingString -> the string that the function will search
# for erasing the spaces after it
def eraseSpacePostAndSay(program, searchingString):
    index = program.find(searchingString)
    oldindex = 0
    while index != -1:
        index = index+oldindex+4
        while program[index] == " ":
            program = program[:index] + program[index+1:]
        oldindex = index
        index = program[index:].find(searchingString)
    return program


# Function for adding the program id to a new process
# input: program -> process without tags
# output: program -> process tagged, changing
# <pid| with the pid of this time unit
def addPid(program):
    index = program.find('<pid|')
    oldindex = 0
    while index != -1:
        index = oldindex+index+1
        pid = str(ntccTime)
        program = program[:index]+pid+program[index+3:]
        oldindex = index+len(pid)
        index = program[oldindex:].find('<pid|')
    return program


# Function for adding the user to a new process
# input:
# program -> process without tags
# user -> the user that will be added to the process
# output: program -> process tagged, changing
# <usn| with the username in the input
def addUser(program, user):
    index = program.find('|usn>')
    oldindex = 0
    while index != -1:
        index = oldindex+index+1
        program = program[:index]+user+program[index+3:]
        oldindex = index+len(user)
        index = program[oldindex:].find('|usn>')
    return program


def addAtUser(program, user):
    index = program.find('usn')
    oldindex = 0
    while index != -1:
        index = oldindex+index+1
        program = program[:index-1]+user+program[index+2:]
        oldindex = index+len(user)
        index = program[oldindex:].find('usn')
    return program


# Function for adding the program id to a new process
# input: program -> process without tags
# output: program -> process tagged, changing
# {pid} with the pid of this time unit
def addPidPosted(program):
    index = program.find('{pid}')
    oldindex = 0
    while index != -1:
        index = oldindex+index
        pid = str(ntccTime)
        program = program[:index]+pid+program[index+5:]
        oldindex = index+len(pid)
        index = program[oldindex:].find('{pid}')
    return program


# Function that increase the ntcc time counter
def ntccTictac(c):
    cl = open(systemfiles+"ntcctime.txt", "w")
    stWrite = str(c+1)
    cl.write(stWrite)
    cl.close()


# Function for adding the program id and user to every post in a process
# input: program -> process without tags
# input: id_user -> username of the user who post the process
# output: program -> process tagged, adding clock and username
# to the messages
def addIdAndOrder(program, id_user):
    index = program.find('post("')
    oldindex = 0
    while index != -1:
        index = oldindex+index+6
        userstr = "<pids|p|" + str(id_user)+">"
        program = program[:index]+userstr+program[index:]
        oldindex = index+len(userstr)
        index = program[oldindex:].find('post("')
    program = addIdAndOrderSignal(program, id_user)
    return program


# Function for adding the program id and user to every post in a process
# input: program -> process without tags
# input: id_user -> username of the user who post the process
# output: program -> process tagged, adding clock and username
# to the messages
def addTagVote(program, id_user):
    index = program.find('vote("')
    oldindex = 0
    while index != -1:
        index = oldindex+index+6
        userstr = "<pids|v|" + str(id_user)+">"
        program = program[:index]+userstr+program[index:]
        oldindex = index+len(userstr)
        index = program[oldindex:].find('vote("')
    program = addIdAndOrderSignal(program, id_user)
    return program


# Function for adding the program id and user to every say in a process
# input: program -> process without tags
# input: id_user -> username of the user who post the process
# output: program -> process tagged, adding clock and username
# to the messages
def addIdAndOrderSignal(program, id_user):
    global ntccTime
    index = program.find('signal("')
    oldindex = 0
    ntccTime = getNtccTime()
    while index != -1:
        index = oldindex + index + 8
        userstr = "<pids|s|" + str(id_user)+">"
        program = program[:index] + userstr + program[index:]
        oldindex = index + len(userstr)
        index = program[oldindex:].find('signal("')
    return program


# Function for adding the program id and user to every say in a process
# input: program -> process without tags
# input: id_user -> username of the user who post the process
# output: program -> process tagged, adding clock and username
# to the messages
def addIdAndOrderSay(program, id_user):
    global ntccTime
    index = program.find('say("')
    oldindex = 0
    ntccTime = getNtccTime()
    while index != -1:
        index = oldindex + index + 5
        userstr = "<pid|s|" + str(id_user)+">"
        program = program[:index] + userstr + program[index:]
        oldindex = index + len(userstr)
        index = program[oldindex:].find('say("')
    program = addIdAndOrderSignal(program, id_user)
    return program


# Function that extract the information of a string that contains a message
def extractInfo(msg):
    clock = ntccTime
    parseResult = parse('<{}>{}', msg)
    if parseResult is None:
        if msg.find("{pid") == -1:
            r = {
                'clock': clock,
                'user_msg': "private",
                'msg': msg, 'class':
                "system"
            }
        else:
            msg = msg.replace("{", "[")
            msg = msg.replace("}", "]")
            r = {
                'clock': clock,
                'user_msg': "private",
                'msg': msg,
                'class': "process"
            }
    else:
        info = parseResult[0]
        message = parseResult[1]
        info = info.split("|")
        r = {
            'clock': info[0],
            'user_msg': info[2],
            'msg': message,
            'class':
            "none"
        }
    return r


# Procedure that load the current state from the txt files
# to the global variables that represent the current memory and processes
def refreshState():
    global processes
    global memory
    memoryFile = open(MEMORY_FILE, "r")
    processFile = open(PROCESS_FILE, "r")
    processes = processFile.readline()
    memory = memoryFile.readline()
    memoryFile.close()
    processFile.close()

refreshState()


# Function that eliminate the first agent of the agents string
# input: agents -> string with agents
# output: agents -> string with agents, but without the first one
def deleteOther(agents):
    stack = []
    index = 0
    for i in agents:
        if i != '[':
            index += 1
        else:
            index += 1
            stack.append("[")
            break
    while index < len(agents):
        i = agents[index]
        if i == '[':
            stack.append("[")
        elif i == ']':
            stack.pop(0)
        index += 1
        if len(stack) == 0:
            break
    index += 3
    return agents[index:]


# Function that choose the first agent of the agents string
# input: agents -> string with agents
# output: agents -> the first agent on the string
def getCurrentAgent(agents):
    stack = []
    index = 0
    for i in agents:
        if i != '[':
            index += 1
        else:
            index += 1
            stack.append("[")
            break
    while index < len(agents):
        i = agents[index]
        if i == '[':
            stack.append("[")
        elif i == ']':
            stack.pop(0)
        index += 1
        if len(stack) == 0:
            break
    return agents[:index]


# Function that convert the agent memory in a json list with every message with
# their information
def convertMemInJson(mem):
    messages = "error"
    memParse = parse("({})", mem)
    if memParse !=  None:
        messages = splitMessages(memParse[0])
    else:

        messages = [mem[1:len(mem)-1]]
    jMessages = []
    for i in messages:
        jMessages.append(extractInfo(i))

    return jMessages


# Function that go through on the memory, searching the space of an agent
# input: agentId -> id of the agent that want to calculate
# output: agents -> the agent memory
def calculateAgentMemory(agentId):
    refreshState()
    parsingResult = parse("{}[{}]", memory)
    agents = parsingResult[1]

    while agentId > 0:
        agents = deleteOther(agents)
        agentId = agentId-1
    agents = getCurrentAgent(agents)

    return agents


# Function that go through on the memory, searching the space of an agent
# input: store -> the store of the system
# input: agentId -> id of the agent that want to calculate
# output: agents -> the agent memory
def calculateAgentMemoryAlpha(store, agentId):
    parsingResult = parse("{}[{}]", store)
    agents = parsingResult[1]
    while agentId > 0:
        agents = deleteOther(agents)
        agentId = agentId-1
    agents = getCurrentAgent(agents)
    return agents


# Function for adding the program id and user to every post in a process
# input: memory -> memory without current pid
# input: timeunit -> current timeunit
# output: memory -> memory with current pid
# on posts
def replacePidAfter(memory, timeunit):
    timeunit = str(timeunit)
    pidStr = '<pids|'
    index = memory.find(pidStr)
    oldindex = 0
    while index != -1:
        index = oldindex+index+1
        memory = memory[:index]+timeunit+memory[index+4:]
        oldindex = index+len(timeunit)
        index = memory[oldindex:].find(pidStr)
    return memory


def createClock(path, timer):
    cron = CronTab(user='dspacenet')
    path = str(path)
    iter = cron.find_comment('p'+path+'$')
    for i in iter:
        cron.remove(i)
    if timer != "0":
        job = cron.new(command=' ~/.nvm/versions/node/v9.4.0/bin/node ~/dspacenet/node/helpers/tickWorker.js ' + path, comment='p'+path+'$')
        job.setall(timer)
    cron.write()


# Procedure that store a successful execution on the memory and processes txt
# files
def saveState(result):
    global ntccTime
    global processes
    global memory
    global memoryDictionary
    ntccTime = getNtccTime()
    parsingResult = parse("result Conf: < {} ; {} >", result)
    processes = parsingResult[0]
    memory = parsingResult[1]
    memory = replacePidAfter(memory, ntccTime)
    mem = open(MEMORY_FILE, "w")
    mem.write(memory)
    mem.close()
    memoryDictionary = {}
    storeMemory(memory)
    clocks = getClocks()
    # notifications = getNotifications()
    # mergeNotifications(notifications)
    print clocks
    i = 0
    while i < len(clocks):
        if clocks[i] != None and clocks[i][0] != '':
            createClock(i, clocks[i][0])
        i += 1
    proc = open(PROCESS_FILE, "w")
    proc.write(processes)
    proc.close()


# Function that get a list of errors and convert it
# into a list of errors in json.
# input: [error1,error2,...,errorN]
# output: [{'error': error1, 'error': error2...,'errorN': errorN}]
def errorToJson(errors):
    jErrors = []
    for i in errors:
        element = {'error': i}
        jErrors.append(element)
    return jErrors


# Routes of the rest server
app = Flask(__name__)


# This route is for looking if the rest server is on
@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'SCCP'})


# This route is for running a program
# It communicate the program to the sccp
# VM and store the result
# For using it.
# input[json]:
# {
#  "config" : "here will be an input process"
#  "user" : "the user who posts the process"
#  "timeu" : "if the timeunit will advance,
#             don't send anything, else, send False"
# }
# output[json]:
# {
#  "result" : "it could be ok or error",
#  "errors" : "if the result is error,
#  here will be the maude errors"
# }
@app.route('/runsccp', methods=['POST'])
def runsccp():
    global ntccTime
    global processes
    ntccTime = getNtccTime()
    refreshState()
    received = request.json['config']
    print "process: " + received
    userP = request.json['user']
    timeunit = str(request.json['timeu'])
    if received == "":
        return jsonify({
            'result': 'error',
            'errors': [{'error': 'empty input'}]
        })
    received = eraseSpacePostAndSay(received, "post")
    received = eraseSpacePostAndSay(received, "say")
    received = addIdAndOrder(received, userP)
    received = addTagVote(received, userP)
    try:
        str(received)
    except:
        errors = errorToJson(["characters not allowed"])
        return jsonify({'result': 'error', 'errors': errors})
    maude.run("red in SCCP-RUN : "+received+" . \n")
    answer = maude.getOutput()
    if answer[0] == "error":
        errors = errorToJson(answer[1])
        return jsonify({'result': 'error', 'errors': errors})
    else:
        parsingResult = parse("result SpaInstruc: {}", answer[1])
        received = parsingResult[0]
    received = addPid(received)
    received = addPidPosted(received)
    received = addUser(received, userP)
    received = addAtUser(received, userP)
    processes = received + " || " + processes
    maude.run("red in NTCC-RUN : IO(< "+processes+" ; "+memory+" >) . \n")
    answer = maude.getOutput()
    if answer[0] == "error":
        errors = errorToJson(answer[1])
        return jsonify({'result': 'error', 'errors': errors})
    else:
        saveState(answer[1])
        if timeunit == "1":
            ntccTictac(ntccTime)
        return jsonify({'result': 'ok'})


@app.route('/getSpace', methods=['POST'])
def getSpace():
    agent = request.json['id']
    path = "0"
    for i in agent:
        path = path+"."+str(i)
    try:
        result = memoryDictionary[path]
        newResult = []
        for i in result:
            newResult.append(extractInfo(i))
        result = newResult
    except:
        result = []
    result.sort(key=lambda clock: int(clock['clock']), reverse=True)
    return jsonify({'result': result})


# This function returns the global memory
@app.route('/getGlobal', methods=['GET'])
def getGlobal():
    # answer = getCurrentAgent(memory)
    parsingResult = parse("{}[{}]", memory)
    if parsingResult[0] is None:
        return jsonify({'result': 'Empty'})
    else:
        answer = convertMemInJson(parsingResult[0])
        answer.sort(key=lambda clock: int(clock['clock']), reverse=True)
        return jsonify({'result': answer})


# Version 30/05/2018 8:18pm
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)
