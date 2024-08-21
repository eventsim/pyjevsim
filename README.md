# PyJEvSim
- PyJEvSim is an event-driven DEVS simulation environment that provides the ability to save and restore models.
---
**Requirements**
1. python >= 3.12 
2. Pyjevsim was developed utilizing existing modules.
   Modules are written in  “Requirements.txt” and can be installed via pip via pip.
   ```
    pip install -r requirements.txt
   ```

-----
**To configure DEVS**
- DEVS(Discrete Event System Specification) consists of a model (Behaivor Model) that describes the behavior and a simulation engine (Systme Executor) that manages and executes the model.

1. Beahavior(Atomic) Model 
   - The atomic model is built by inheriting from Pyjevsim's BehaivorModel.
   - Models inherit the BehaviorModels’s framework and use it by implementing the model's int_trans (internal transition function), ext_trans (external transition function), and output (output function).
   - The input and output of each model are managed through “port” of str type. 
   - Also, data is passed between models through SysMessage. 

   1. Construct a model that inherits from pyjevsim's BehaviorModel.
      ```
      #Basic module import data
      from pyjevsim.behavior_model import BehaviorModel
      from pyjevsim.definition import *
      from pyjevsim.system_message import SysMessage 
      ```
   2. Behavior Model : init
      ```
      class BM_Exmaple(BehaviorModel):
      	def __init__(self, name):
      		BehaviorModel.__init__(self, name)     
      		#Typically insert a State or port       
      ```
   3. Manage status
      1. Insert State
         ```
         insert_input_port(name, deadline)
         
         #Args 
         	#name(str) : state name 
         	#deadline(int or Infinite) : state deadline
         ``` 
      2. Setting the state
         ```
         init_state(state)
         
         #Args
         	#state(str) : init state name 
         ```
      
         ```
         #_cur_state : Current state of the model
         ```
   4. insert port
      ``` 
      insert_input_port(port) # insert input port 
      insert_output_port(port) # insert output port   
      
      #Args 
      	#port(str) : port name 
      ``` 
   5. ext_trans : External transition function
      ``` 
      def ext_trans(self, port, msg):
      	#ext_trans
      
      	return None
      
      #Args:
      	#port (str) : 
          #msg  (SysmMessage) : pyjevsim SysMessage type 
      ``` 
   6. output : Output function 
      ``` 
      def output(self):
      	#output 
      
      	msg = SysMessage(self.get_name(), output_port)
      	#output_port(str) : model output port
      
      	return msg
      ``` 
   7. int_trans : Internal transition function
      ``` 
      def int_trans(self):
         	 #int_trans
       
         	return None
      ```
2. SysExecutor(Simulation Engine)
   - The SysExecutor manages simulation time, executes models, and manages the relationships between models.
   - It also manages the ModelSnapshotManager, which performs snapshot/restore of the model.
   1. Configuring SysExecutor
      ```
      #Basic module import data
      from pyjevsim.definition import *
      from pyjevsim.system_executor import SysExecutor
      
      #Configured models data
      ```
   2. SysExecutor init  
      ```
      se = SysExecutor(t_resol, "defalut", ex_mode=execution_mode, sapshot_manager=None)
      
      #tresol(float): The time resolution for the simulation
      #_sim_name (str, optional): The name of the simulation
      #ex_mode (R_TIME or VTIME): The execution mode(Real time or Virtual time)
      #snapshot_manager (ModelSnapshotManager, optional): Manages SnapshotExecutor
      ```
   3. Register Model & Relation
      ```
      se.register_entity(gen) #se : SysExecutor
      se.register_entity(proc) #gen & proc : BehaviorModel
      
      # Related Model's input/output ports to each other. 
      
      # se : SysExecutor to relate as output ports 
      # "start" : se's output port
      # gen : Model to relate as input ports 
      # "start" : gen's inpupt port
      
      se.coupling_relation(se, "start", gen, "start")
      se.coupling_relation(gen, "process", proc, "recv")
      ```
   4. Insert event
      ```
      se.insert_external_event(_port = "start", _msg = None, scheduled_time = 0)
      
      #Args:
       #_port (str): port name
       #_msg (SysMessage or None): Event message
       #scheduled_time (float, optional): The scheduled time for the event
      ```
3. SysMessage
   - SysMessage for handling messages(port and data) between Models.
   1. SysMessage init
      ```
      msg = SysMessage(src_name = self.get_name(), dst_name = "process")
      
      #Args:
      # src_name (str): The source name(Model name)
      # dst_name (str): The destination name(port)
      ```
   2. Message insert : Inserts a message into the message list(data).
      ```
      msg.insert("data")  # Insert message data, The data can be any type
      ```
   3. Message
      ```
      data = msg.retrieve()  #retrieve message data list
      ```

  ----
**BehaviorModel Snapshot Manual**
- To snapshot a model, set up BehavioralModel and SnapshotExecutor at Snapshot Manager.
- Then assign the set ModelSnapshotManager to the SysExecutor. 

1. SnapshotExecutor  
   - SnapshotExecutor is a framework for adding snapshot conditions to behavior models.
   - You inherit from SnapshotExecutor and enter a snapshot condition. 
   - Snapshot conditions can be written at time increments or before or after functions in the behavior model. 
   ```
   class ExmapleSnapshotExecutor(SnapshotExecutor) :
    	@staticmethod
    	def create_executor(behavior_executor) :
       	return ExmapleSnapshotExecutor(behavior_executor) 
   		#Name of created class
    
    	def __init__(self, behavior_executor):
        	super().__init__(behavior_executor)
   ```
   - snapshot
     - An abstract method that creates a method to take a snapshot.
     - You can use the snapshot method in a conditional method.
     - Use the model_dump method to get the model data in bytes. 
     - Save that data to the DB or save it to a file.
     ```
     @abstractmethod
     def snapshot(self, name):
         #name (str): The name of the snapshot
     	pass
     ```
   - snapshot_time_condition: Functions that allow you to enter conditions based on time increments.
     ```
     @abstractmethod
     def snapshot_time_condition(self, global_time):
     """Abstract method for snapshot time condition.
          
     Args:
     global_time (float): The global time / simulation time
     """
     pass #Write your conditions.
     ```
   - You can enter snapshot conditions before and after the ext_trans, int_trans, and output functions are executed.
     The arguments are the same as for each function.
     ```
     snapshot_pre_condition_ext #executed prior to running text_trans
     snapshot_post_condition_ext #executed after the #ext_trans run
       
     snapshot_pre_condition_int #executed before running int_trans
     snapshot_post_condition_int #executed after running int_trans
       
     snapshot_pre_condition_out #executed before running output
     snapshot_post_condition_out #executed after output execution
     ```
2. ModelSnapshotManager : Set the ModelSnapshotManager to SysExecutor.
   ```
   snapshot_manager = ModelSnapshotManager() #Set ModelSnapshotManager
   ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=snapshot_manager) # Set up snapshot manager in SysExecutor
   ```
3. register_snapshot_executor : Register the SnapshotExecutor with the ModelSnapshotManager.
   ```
   snapshot_manager.register_snapshot_executor(name = "model_name", snapshot_executor_generator = BankGenModelSnapshotExecutor.create_executor)
   
   #name (str): name of SnapshotExecutor
   #snapshot_executor_generator : The generator function for SnapshotExecutor
   ```
**BehaviorModel Restore Manual**
1. ModelSnapshotManager : Set the ModelSnapshotManager.
   ```
   snapshot_manager = ModelSnapshotManager() #Set ModelSnapshotManager
   ```
2. load_snapshot : Restore SnapshotData to BehaviorModel
   ```
   gen = snapshot_manager.load_snapshot(name = "gen", shotmodel = snapshot_data)
   
   #Args:
    #name (str): The name of Model
    #shotmodel (bytes): Binary data of the model snapshot
   
   #Returns:
    #object(BehaivorModel): The loaded model
        
   #Raises:
    #Exception: If the model type is not ModelType.BEHAVIORAL
   ```
-----
**Simulation Snapshot Manual**
- Snapshots of simulations (models registered in the SysExecutor and releases of models) are possible over time.
- The running simulation is saved locally in a file format.

1. ModelSnapshotManager : Set the ModelSnapshotManager to SysExecutor.
   ```
   snapshot_manager = ModelSnapshotManager() #Set ModelSnapshotManager
   ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=snapshot_manager) # Set up snapshot manager in SysExecutor
   ```
2. snapshot_simulation : As the simulation time increases, when the conditions are satisfied, the Snapshot.
   ```
   ss.snapshot_simulation(name = "banksim", directory_path = "./snapshot")
   
   #name(str) : Name of the simulation to be snapshot
   #directory_path : Where the simulation will be snapshot
   ```

**Simulation Restore Manual**
1. SnapshotManager : Set the SnapshotManager.
   ```
   snapshot_manager = SnapshotManager(t_resol, ex_mode=execution_mode, name = "banksim", path = "./snapshot")   
   
   #t_resol(float) SysExecutor's time resolution to be restored with the saved model and connection information between models
   #ex_mode (R_TIME or V_TIME): Execution mode(Real time or Virtual time)
   #name (str): Name of SysExecutor
   #path (str, optional): Path to load snapshots
   ```
2. get_engine : Restored SysExecutor
   ```
   ss = snapshot_manager.get_engine()
   ```
-----
**test code : ./tests**
- A GBP example is written in tests where you can experiment with basic DEVS.
  - GBP Example: BehaviorModel (DEVS Atomic Model)
    ```
    pytest -s tests/test_behavior_model.py
    ```
  - GBP Example: Structural (DEVS Coupled Model)
    ```
      pytest -s tests/test_structural.py
    ```
  - GBP Example: Hierarchical (DEVS Atomic Model & Coupled Model)
    ```
      pytest -s tests/test_hierarchical.py
    ```
  **test code : ./test_banksim**
- In addition, a BankSim example is written in test_banksim where you can store DEVS, BehaivorModel Snapshot and Simulation. 
  - banksim_classic.py : classic Bank Simulation
    ```
    pytest -s test_banksim/banksim_classic.py
    ```
  - banksim_model_snapshot.py : BehavioralModel snapshots example
    ```
    pytest -s test_banksim/banksim_model_snapshot.py
    ```
  - banksim_model_restore.py : Restored a model saved from banksim_model_snapshot
    ```
    pytest -s test_banksim/banksim_model_restore.py
    ```
  - banksim_snapshot.py : Simulation(Model & Relation) snapshots example
    ```
    pytest -s test_banksim/banksim_snapshot.py
    ```
  - banksim_restore.py : Restored Simulation(Model & Relation) saved from banksim_snapshot
    ```
    pytest -s test_banksim/banksim_restore.py
    ```
