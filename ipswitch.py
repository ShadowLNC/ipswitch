from subprocess import check_output as shell_exec
from sys import argv
import re
from time import sleep   

sysargs = argv[1:]
#print(sys.argv)
rawlist = shell_exec("wmic nic get Index, NetConnectionID, NetConnectionStatus", universal_newlines=True)
rawlist = [i for i in rawlist.split("\n") if i]

#process field lengths
fieldlengths = []
lastchar = 'a' #anything but a space
charcount = 0
for char in rawlist[0]:
    #cut field lengths at end of spaces on header row
    if char!=' ' and lastchar==' ':
        fieldlengths.append(charcount)
        charcount = 0 #would be -1 but first char
    charcount += 1
    lastchar = char
fieldlengths.append(charcount)
del charcount, lastchar

#process fields
adapters = []
for line in rawlist[1:]:
    fields = []
    for i,field in enumerate(fieldlengths):
        low = sum(fieldlengths[:i])
        fields.append(line[low:low+field])

    # we only care about NetConnectionID but Index and NetConnectionStatus
    # must also be populated to satisfy requirements
    if all([i.strip() for i in fields]):
        adapters.append(fields[1].strip())
if len(adapters)<=0: raise OSError("You don't have any network adapters...")

#team number
text = "Team Number: "
team = sysargs[0] if len(sysargs)>0 else input(text)
while not re.search("^[1-9][0-9]{0,3}$", team):
    team = input("Error: Team Number must be between 1 and 9999\n" + text)
team = int(team)
del text
#if team>9999 or team<=0: raise ValueError("Team Number must be between 1 and 9999")

#ip mode
text = ("Setup Method:\n" +
    "0 Normal (Non-FRC)\n" +
    "1 Wired cRIO\n" +
    "2 Wireless cRIO\n" +
    "> ")
state = sysargs[1] if len(sysargs)>1 else input(text)
while not re.search("^[0-2]$", state):
    state = input("Error: Setup Method must be between 0 and 2\n" + text)
state = int(state)
del text
#if state>2 or state<0: raise ValueError("State must be between 0 and 2")
state_ips = [-1, 5, 9]

#adapter to use
live = -1 #placeholder to make i==live be false
if state>0:
    #filter wired/wireless
    filtered = list(filter(lambda a: (state==1) ^ ("wireless" in a.lower()), adapters))
    #filtered = [i for i in adapters if state==1 ^ ("wireless" in i.lower())]
    if not len(filtered): filtered = list(adapters) #backup if no unfiltered adapters
    
    if len(filtered)==1:
        live = adapters.index(filtered[0])
        print("Auto-Selecting \"{}\" as only wire{} adapter".format(filtered[0], "d" if state==1 else "less"))
    else:
        text = ("Which adapter would you like to use?\n" +
            '\n'.join(["{} {}".format(i,name) for i,name in enumerate(filtered)]) + '\n' +
            "> ")
        live = sysargs[2] if len(sysargs)>2 else input(text)
        while (not re.search("^[0-9]*$", live)) or int(live)>=len(filtered):
            live = input("Adapter Selection must be between 0 and {:d}\n".format(len(filtered)) + text)
        live = adapters.index(filtered[int(live)])
        del text
        #if live>=len(adapters) or live<0: raise ValueError("Adapter must be between 0 and 1 less than number of adapters")

#change adapter settings
for i,a in enumerate(adapters):
    enable = (state==0 or i==live)
    
    # wmic path win32_networkadapter where NetConnectionID=<NETCONNECTIONID> call en/disable
    cmd = "wmic path win32_networkadapter where NetConnectionID=\"{}\" call {}able".format(a, ("en" if enable else "dis"))
    #print(cmd)
    out = shell_exec(cmd)
    #print(out)
    del cmd, out
    
    if enable:
        # wait for adapter to enable if previously disabled
        # change time as necessary, YMMV
        sleep(0.09)
        
        # netsh interface ip set address <NAME> <SOURCE> <ADDR> <MASK> <GATEWAY> <GWMETRIC>
        cmd = "netsh interface ip set address name=\"{}\" source=".format(a)
        
        if state>0:
            #i==live
            base_ip = "10.{:.0f}.{:d}.".format(team/100, team%100)
            ipcmd = "static addr={0}{1:d} mask=255.0.0.0 gateway={0}1 gwmetric=0".format(base_ip, state_ips[state])
            cmd += ipcmd
        else: cmd += "dhcp"

        #print(cmd)
        out = shell_exec(cmd)
        #print(out)
        del cmd, out
