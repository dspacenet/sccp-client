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


def ntccTicTac():
    """
    Function that increase the ntcc time counter
    """
    global ntccTime
    ntccTime += 1
    cl = open(systemfiles+"ntcctime.txt", "w")
    cl.write(str(ntccTime))
    cl.close()


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
    processes, memory = parse("result Conf: < {} ; {} >", result)
    memory = memory.replace('<pids|', '<'+str(ntccTime)+'|')
    memoryFile = open(MEMORY_FILE, "w")
    memoryFile.write(memory)
    memoryFile.close()
    memoryDictionary = {}
    storeMemory(memory)
    clocks = getClocks()
    i = 0
    while i < len(clocks):
        if clocks[i] is not None and clocks[i][0] != '':
            createClock(i, clocks[i][0])
        i += 1
    processesFile = open(PROCESS_FILE, "w")
    processesFile.write(processes)
    processesFile.close()


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
    program = request.json['config']
    user = request.json['user']
    updateClock = str(request.json['timeu'])
    if program == "":
        return jsonify({
            'result': 'error',
            'errors': [{'error': 'empty input'}]
        })
    try:
        str(program)
    except:
        errors = errorToJson(["characters not allowed"])
        return jsonify({'result': 'error', 'errors': errors})
    print "Running process: " + program
    maude.run("red in SCCP-RUN : "+program+" . \n")
    answer = maude.getOutput()
    if answer[0] == "error":
        errors = errorToJson(answer[1])
        return jsonify({'result': 'error', 'errors': errors})
    else:
        parsingResult = parse("result SpaInstruc: {}", answer[1])
        program = parsingResult[0]
    program = program.replace('<pid|','<'+str(ntccTime)+'|')
    program = program.replace('{pid}', str(ntccTime))
    program = program.replace('|usn>','|'+user+'>')
    program = program.replace('usn', user)
    processes = program + " || " + processes
    maude.run("red in NTCC-RUN : IO(< "+processes+" ; "+memory+" >) . \n")
    answer = maude.getOutput()
    if answer[0] == "error":
        errors = errorToJson(answer[1])
        return jsonify({'result': 'error', 'errors': errors})
    else:
        saveState(answer[1])
        if updateClock == "1":
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
