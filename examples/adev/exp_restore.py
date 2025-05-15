import contexts
import sys,os

from pyjevsim.system_executor import SysExecutor
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.definition import *
from pyjevsim.restore_handler import RestoreHandler

from config import *

from examples.adev.clock import Clock
from examples.adev.core_component import HumanType
from examples.adev.core_component import FamilyType

from examples.adev.job import *

from examples.adev.human import Human
from examples.adev.check import Check
from examples.adev.government import Government
from examples.adev.garbagecan import GarbageCan
from examples.adev.garbage_truck import GarbageTruck
from examples.adev.family import Family


max_simtime = 1000

scenario = "restore_scenario"

snapshot_manager = SnapshotManager(RestoreHandler(TIME_DENSITY, ex_mode=SIMULATION_MODE, name = "adev300", path = "./snapshot"))  
se = snapshot_manager.get_engine() #Restore a snapshot simulation

"""
outputlocation=str("./output/")+str(scenario)+str(TIME_STDDEV)+"trash"+str(TRASH_STDDEV)+"_"+str(GARBAGECAN_SIZE)
if not os.path.exists(outputlocation):
    os.makedirs(outputlocation)
else:
    outputlocation = None

blist=[]
hlist=[]
fam=[]

file = open("./scenario/"+scenario+".txt",'r')
lines = file.readlines()
file.close()
for i in range(len(lines)):  
    line = lines[i].split('\n')[0]
    if not line == "": #빈칸이 아닐경우
        elements = (line.split(','))
        for j in elements: #패밀리 안의 멤버=j
            fam.append(eval(j)) #j를 fam추가
        hlist.append(fam) #fam을 hlist에 추가
        fam=[]    
    else:
        blist.append(hlist)
        hlist = []
    if i == len(lines)-1:
        blist.append(hlist)
        

gt = se.get_model("garbage_truck")
gv = se.get_model("government")

i=0
j=0
for building in blist:


    g = GarbageCan("gc[{0}]".format(i), GARBAGECAN_SIZE, outputlocation)
    se.register_entity(g)
    
    for flist in building:
        ftype = FamilyType(TEMP_CAN_SIZE)
        f = Family("family", ftype)
        se.register_entity(f)
        
        for htype in flist:
            #hid = get_human_id()
            name = htype.get_name()
            cname = "check[{0}]".format(htype.get_name())
            #print(name)               
            h1 = Human(cname, htype)
            ch = Check(name, htype)

            se.register_entity(h1)
            se.register_entity(ch)
            #f1.register_member(htype)
            ftype.register_member(htype)
            
            # Connect Check & Can
            ports = g.register_human(htype.get_id())
            se.coupling_relation(h1, "trash", ch, "request")
            se.coupling_relation(ch, "check", g, ports[0])

            se.coupling_relation(g, ports[1], ch, "checked")
            se.coupling_relation(ch, "gov_report", gv, "recv_report")
    
            se.coupling_relation(None, "start", h1, "start")
            se.coupling_relation(None, "end", h1, "end")
            se.coupling_relation(h1, "trash", f, "receive_membertrash")
            
        ports = g.register_family(j)
        se.coupling_relation(f, "takeout_trash", g, ports[0])
        j+=1

    # Connect Truck & Can
    ports = gt.register_garbage_can(i)
    se.coupling_relation(g, "res_garbage", gt, ports[0])
    se.coupling_relation(gt, ports[1], g, "req_empty")
    i+=1

"""


se.insert_input_port("start")

se.insert_external_event("start", None)

for i in range(max_simtime) :
    se.simulate(1)


