from flask import Flask, jsonify, request
from parse import parse
from maude import MaudeProcess
from crontab import CronTab
import os

# Structure of messages: "<clock,id_user>message"
# System files are located inside the following directory
systemfiles = "~systemfiles/"
MEMORY_FILE = systemfiles+"memory.txt"
PROCESS_FILE = systemfiles+"process.txt"


# Definition of some global variables
maude = MaudeProcess()
memory = ""
ntccTime = 0
memoryDictionary = {}


def setNtccTime():
    """
    This function get the ntcc time counter, it's stored in a txt file
    """
    global ntccTime
    cl = open(systemfiles+"ntcctime.txt", "r")
    time = cl.readline()
    cl.close()
    ntccTime = int(time)


def splitMessages(stringMessages):
    """
    Function that obtains every message inside a string of messages from the
    memory of an agent

    Arguments: stringMessages {string} -- '"message 1", "message 2"...'

    Returns: [string] -- ['message 1', 'message 2', 'message 3' ...]
    """
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
    while memoryDictionary.get(space) is not None:
        i += 1
        clocks.append(memoryDictionary.get(space+".6"))
        space = base+str(i)
    return clocks


def getNotifications():
    base = "0."
    i = 0
    space = base+str(i)
    notifications = []
    while memoryDictionary.get(space) is not None:
        i += 1
        notifications.append(memoryDictionary.get(space+".10"))
        space = base+str(i)
    return notifications


def storeNotifications(notifications):
    return 0


def addPid(program):
    """Function for adding the program id to a new process

    Arguments:
        program {string} -- process without tags

    Returns:
        string -- process tagged, changing <pid| with the pid of this time unit
    """
    index = program.find('<pid|')
    oldindex = 0
    while index != -1:
        index = oldindex+index+1
        pid = str(ntccTime)
        program = program[:index]+pid+program[index+3:]
        oldindex = index+len(pid)
        index = program[oldindex:].find('<pid|')
    return program


def addUser(program, user):
    """Function for adding the user to a new process

    Arguments:
        program {string} -- process without tags
        user {string} -- the user that will be added to the process

    Returns:
        string -- process tagged, changing with the username in the input
    """
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


def addPidPosted(program):
    """Function for adding the program id to a new process

    Arguments:
        program {string} -- process without tags

    Returns:
        string -- process tagged, changing {pid} with the pid of this time unit
    """

    index = program.find('{pid}')
    oldindex = 0
    while index != -1:
        index = oldindex+index
        pid = str(ntccTime)
        program = program[:index]+pid+program[index+5:]
        oldindex = index+len(pid)
        index = program[oldindex:].find('{pid}')
    return program


def ntccTicTac():
    """
    Function that increase the ntcc time counter
    """
    global ntccTime
    ntccTime += 1
    cl = open(systemfiles+"ntcctime.txt", "w")
    cl.write(str(ntccTime))
    cl.close()


def addIdAndOrder(program, id_user):
    """Function for adding the program id and user to every post in a process

    Arguments:
        program {string} -- process without tags
        id_user {string} -- username of the user who post the process

    Returns:
        string -- process tagged, adding clock and username to the messages
    """
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


def addTagVote(program, id_user):
    """Function for adding the program id and user to every post in a process

    Arguments:
        program {string} -- process without tags
        id_user {string} -- username of the user who post the process

    Returns:
        string -- process tagged, adding clock and username to the messages
    """
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


def addIdAndOrderSignal(program, id_user):
    """Function for adding the program id and user to every say in a process

    Arguments:
        program {string} -- process without tags
        id_user {string} -- username of the user who post the process

    Returns:
        string -- process tagged, adding clock and username to the messages
    """
    index = program.find('signal("')
    oldindex = 0
    while index != -1:
        index = oldindex + index + 8
        userstr = "<pids|s|" + str(id_user)+">"
        program = program[:index] + userstr + program[index:]
        oldindex = index + len(userstr)
        index = program[oldindex:].find('signal("')
    return program


def extractInfo(msg):
    """Function that extract the information of a string that contains a message

    Arguments:
        msg {string} -- original message

    Returns:
        string -- message extracted
    """
    clock = ntccTime
    parseResult = parse('<{}>{}', msg)
    if parseResult is None:
        if msg.find("{pid") == -1:
            r = {
                'clock': clock,
                'user_msg': "private",
                'msg': msg,
                'class': "system"
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


def refreshState():
    """
    Procedure that load the current state from the txt files
    to the global variables that represent the current memory and processes
    """
    global processes
    global memory
    memoryFile = open(MEMORY_FILE, "r")
    processFile = open(PROCESS_FILE, "r")
    processes = processFile.readline()
    memory = memoryFile.readline()
    memoryFile.close()
    processFile.close()


def deleteOther(agents):
    """Function that eliminate the first agent of the agents string

    Arguments:
        agents {string} -- string with agents

    Returns:
        string -- string with agents, but without the first one
    """

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


def getCurrentAgent(agents):
    """Function that choose the first agent of the agents string

    Arguments:
        agents {string} -- string with agents

    Returns:
        string -- the first agent on the string
    """
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


def convertMemInJson(mem):
    """
    Function that convert the agent memory in a json list with every message
    with their information

    Arguments: mem {Dict} -- memory dictionary

    Returns: string -- JSON string
    """
    messages = "error"
    memParse = parse("({})", mem)
    if memParse is not None:
        messages = splitMessages(memParse[0])
    else:
        messages = [mem[1:len(mem)-1]]
    jMessages = []
    for i in messages:
        jMessages.append(extractInfo(i))

    return jMessages


def calculateAgentMemory(agentId):
    """Function that go through on the memory, searching the space of an agent

    Arguments:
        agentId {int} -- id of the agent that want to calculate

    Returns:
        string -- the agent memory
    """
    parsingResult = parse("{}[{}]", memory)
    agents = parsingResult[1]
    while agentId > 0:
        agents = deleteOther(agents)
        agentId -= 1
    agents = getCurrentAgent(agents)

    return agents


def replacePidAfter(memory, timeunit):
    """Function for adding the program id and user to every post in a process

    Arguments:
        memory {string} -- memory without current pid
        timeunit {int} -- current timeunit

    Returns:
        [type] -- memory with current pid
    """
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
        job = cron.new(command=' ~/.nvm/versions/node/v9.4.0/bin/node ~/dspacenet/api/tickWorker.js ' + path, comment='p'+path+'$')
        job.setall(timer)
    cron.write()


def saveState(result):
    """Procedure that store a successful execution on the memory and processes txt

    Arguments:
        result {string} -- result of the execution
    """
    global processes
    global memory
    global memoryDictionary
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
    i = 0
    while i < len(clocks):
        if clocks[i] is not None and clocks[i][0] != '':
            createClock(i, clocks[i][0])
        i += 1
    proc = open(PROCESS_FILE, "w")
    proc.write(processes)
    proc.close()


def errorToJson(errors):
    """
    Function that gets a list of errors and converts it into a list of errors
    in json.

    Arguments: errors {[type]} -- [error1,error2,...,errorN]

    Returns: [type] -- [{'error': error1, 'error': error2...,'errorN': errorN}]
    """
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
def runSCCP():
    global processes
    received = request.json['config']
    print "Running process: " + received
    userP = request.json['user']
    timeunit = str(request.json['timeu'])
    if received == "":
        return jsonify({
            'result': 'error',
            'errors': [{'error': 'empty input'}]
        })
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
            ntccTicTac()
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
    parsingResult = parse("{}[{}]", memory)
    if parsingResult[0] is None:
        return jsonify({'result': 'Empty'})
    else:
        answer = convertMemInJson(parsingResult[0])
        answer.sort(key=lambda clock: int(clock['clock']), reverse=True)
        return jsonify({'result': answer})


# Version 30/05/2018 8:18pm
if __name__ == '__main__':
    setNtccTime()
    refreshState()
    storeMemory(memory)
    app.run(host='0.0.0.0', port=8082)
