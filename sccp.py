from flask import Flask, jsonify, request
from parse import parse
from maude import MaudeProcess
from crontab import CronTab
import os

# Structure of messages: "<clock,id_user>message"
# System files are located inside the following directory
SYSTEM_FILES_PATH = "~systemfiles/"
MEMORY_FILE = SYSTEM_FILES_PATH+"memory.txt"
PROCESS_FILE = SYSTEM_FILES_PATH+"process.txt"
NTCC_TIME_FILE = SYSTEM_FILES_PATH+"ntcctime.txt"


# Definition of some global variables
maude = MaudeProcess()
rawMemory = ""
ntccTime = 0
memory = {}


def setNtccTime():
    """
    This function get the ntcc time counter, it's stored in a txt file
    """
    global ntccTime
    ntccTimeFile = open(NTCC_TIME_FILE, "r")
    ntccTime = int(ntccTimeFile.readline())
    ntccTimeFile.close()


def splitMessages(stringMessages):
    """
    Function that obtains every message inside a string of messages from the
    memory of an agent

    Arguments: stringMessages {string} -- '"message 1", "message 2"...'

    Returns: [string] -- ['message 1', 'message 2', 'message 3' ...]
    """
    messages = []
    message = ""
    quoteCounter = 0
    for c in stringMessages:
        if c == '"':
            quoteCounter += 1
        elif c == "," and quoteCounter % 2 == 0:
            messages.append(message)
            message = ""
        elif quoteCounter % 2 != 0:
            message = message+c
    messages.append(message)
    return messages


def storeChild(memory, stack, i):
    global memory
    path = str(stack[0])
    for j in stack[1:]:
        path = path+"."+str(j)
    agentString = memory[i:]
    index = agentString.find("[")
    if index != -1:
        agentString = agentString[:index]
        messages = splitMessages(agentString)
        memory[path] = messages
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
    while memory.get(space) is not None:
        i += 1
        clocks.append(memory.get(space+".6"))
        space = base+str(i)
    return clocks


def ntccTicTac():
    """
    Function that increase the ntcc time counter
    """
    global ntccTime
    ntccTime += 1
    ntccTimeFile = open(NTCC_TIME_FILE, "w")
    ntccTimeFile.write(str(ntccTime))
    ntccTimeFile.close()


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
            'class': "none"
        }
    return r


def refreshState():
    """
    Procedure that load the current state from the txt files
    to the global variables that represent the current memory and processes
    """
    global processes
    global rawMemory
    memoryFile = open(MEMORY_FILE, "r")
    processFile = open(PROCESS_FILE, "r")
    processes = processFile.readline()
    rawMemory = memoryFile.readline()
    memoryFile.close()
    processFile.close()


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
    global rawMemory
    global memory
    processes, rawMemory = parse("result Conf: < {} ; {} >", result)
    rawMemory = rawMemory.replace('<pids|', '<'+str(ntccTime)+'|')
    memoryFile = open(MEMORY_FILE, "w")
    memoryFile.write(rawMemory)
    memoryFile.close()
    memory = {}
    storeMemory(rawMemory)
    clocks = getClocks()
    i = 0
    while i < len(clocks):
        if clocks[i] is not None and clocks[i][0] != '':
            createClock(i, clocks[i][0])
        i += 1
    processesFile = open(PROCESS_FILE, "w")
    processesFile.write(processes)
    processesFile.close()


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
    # TODO: throw errors using HTTP status codes
    global processes
    # Retrieve arguments from request
    program = request.json['config']
    user = request.json['user']
    updateClock = str(request.json['timeu'])
    # Throw error if program is empty
    if program == "":
        return jsonify({'result': 'error', 'errors': ['empty input']})
    # Throw error if program contains spacial characters
    # TODO: string handling should be done using unicode, so this check won't
    #   be necessary
    try:
        str(program)
    except:
        return jsonify({'result': 'error', 'errors': ["characters not allowed"]})
    # Log process to be executed
    print "Executing process: " + program
    # SCCP Step: translate program to SCCP
    maude.run("red in SCCP-RUN : "+program+" . \n")
    result, data, _ = maude.getOutput()
    # If error, throw
    if result == "error":
        return jsonify({'result': 'error', 'errors': data})
    # Get translated program from maude response
    program = parse("result SpaInstruc: {}", data)[0]
    # Pre-NTCC Step: patch program to correctly include username and pid.
    program = program.replace('<pid|', '<'+str(ntccTime)+'|')
    program = program.replace('{pid}',  str(ntccTime))
    program = program.replace('|usn>', '|'+user+'>')
    program = program.replace('usn', user)
    # NTCC Step: execute program along with the other existent process
    processes = program + " || " + processes
    maude.run("red in NTCC-RUN : IO(< "+processes+" ; "+rawMemory+" >) . \n")
    result, data, _ = maude.getOutput()
    # if error, throw
    if result == "error":
        return jsonify({'result': 'error', 'errors': data})
    # store data to update system status
    saveState(data)
    # update clock if flag is set
    if updateClock == "1":
        ntccTicTac()
    # Reply with status OK
    return jsonify({'result': 'ok'})


@app.route('/getSpace', methods=['POST'])
def getSpace():
    path = "0"
    if ('path' in request.json):
        path += "." + str(request.json['path'])
    try:
        space = memory[path]
        newResult = []
        for i in space:
            newResult.append(extractInfo(i))
        space = newResult
    except:
        space = []
    space.sort(key=lambda clock: int(clock['clock']), reverse=True)
    return jsonify({'result': space})


# Version 30/05/2018 8:18pm
if __name__ == '__main__':
    # TODO: Initialice system files is not files not found
    setNtccTime()
    refreshState()
    storeMemory(rawMemory)
    app.run(host='0.0.0.0', port=8082)
