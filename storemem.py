d = {}
from parse import *

ntcctime=15

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
    global d
    path = str(stack[0])
    for j in stack[1:]:
        path=path+"."+str(j)
    agentString=memory[i:]
    index=agentString.find("[")
    if index!= -1:
        agentString=agentString[:index]
        messages=splitMessages(agentString)
        d[path] = messages
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

#mem= 'empty[empty[empty-forest] : ( "<480|hectordavid1228|p>hello everyone, this is a test", "<484|hectordavid1228|p>post(%22new%20post%22)")[empty[empty-forest] : empty[empty-forest] : ( "<480|hectordavid1228> post(hello everyone, this is a test)", "<484|hectordavid1228> npost(post(%22new%20post%22))")[empty-forest] : empty-forest] : "<481|hectordavid1228|p>hello%20frank%20this%20is%20a%20test"[empty[ empty-forest] : empty[empty-forest] : "<481|hectordavid1228> npost(hello%20frank%20this%20is%20a%20test)"[ empty-forest] : empty-forest] : ( "<482|hectordavid1228|p>hello%20frank,%20this%20is%20a%20test", "<483|hectordavid1228|p>post(%22im%20sorry%20camilo,%20this%20is%20a%20test%22)")[empty[ empty-forest] : empty[empty-forest] : ( "<482|hectordavid1228> npost(hello%20frank,%20this%20is%20a%20test)", "<483|hectordavid1228> npost(post(%22im%20sorry%20camilo,%20this%20is%20a%20test%22))")[empty-forest] : empty-forest] : empty-forest]'
msg="<480|p|hectordavid1228>hello everyone, this is a test"
print extractInfo(msg)
#storeMemory(mem)
#print d