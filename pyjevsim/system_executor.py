"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module includes SysExecutor, a simulation engine that manages models over time. 
"""

import copy
import datetime
import heapq
import math
import threading
import time
from collections import deque

from .core_model import CoreModel
from .default_message_catcher import DefaultMessageCatcher
from .definition import ExecutionType, Infinite, ModelType, SimulationMode
from .executor_factory import ExecutorFactory
from .schedule_queue import ScheduleQueue
from .system_message import SysMessage
from .termination_manager import TerminationManager

from .message_deliverer import MessageDeliverer

class SysExecutor(CoreModel):
    """The pyjevsim simulation engine.

    ``SysExecutor`` manages simulated time, the future-event list, model
    couplings, and registered executors. At each simulated instant it collects
    outputs before applying internal, external, or confluent transitions.

    Three execution modes are supported via :class:`ExecutionType`:

    - ``V_TIME`` jumps to the next scheduled event.
    - ``R_TIME`` advances by ``time_resolution`` and follows wall-clock pace.
    - ``HLA_TIME`` advances through calls to :py:meth:`step` with an RTI grant.
    """

    EXTERNAL_SRC = "SRC"
    EXTERNAL_DST = "DST"

    def __init__(self, _time_resolution, _sim_name="default",
                 ex_mode=ExecutionType.V_TIME, snapshot_manager=None,
                 track_uncaught=False):
        """
        Initializes the SysExecutor with time resolution, simulation name, execution mode, and optional snapshot manager.

        Args:
            _time_resolution (float): The time resolution for the simulation
            _sim_name (str, optional): The name of the simulation
            ex_mode (ExecutionType): The execution mode — one of
                ``V_TIME`` (virtual time, jump-to-next-event),
                ``R_TIME`` (real time, ``time_resolution``-stepped),
                or ``HLA_TIME`` (federate-driven via
                :py:meth:`step`).
            snapshot_manager (ModelSnapshotManager, optional): Manages SnapshotExecutor
            track_uncaught (bool, optional): Route output from uncoupled ports
                to :class:`DefaultMessageCatcher`. Defaults to ``False``.
        """
        CoreModel.__init__(self, _sim_name, ModelType.UTILITY)
        self.condition = threading.Condition()
        self._track_uncaught = bool(track_uncaught)

        self.global_time = 0
        self.target_time = 0
        self.time_resolution = _time_resolution

        # dictionary for waiting simulation objects
        self.waiting_obj_map = {}
        self._waiting_keys = []  # min-heap of creation times
        # dictionary for active simulation objects
        self.active_obj_map = {}

        # dictionary for object to ports
        self.product_port_map = {}
        self.port_map = {}


        self.hierarchical_structure = {}
        self.model_map = {}
        
        # ScheduleQueue groups executors by request time and keeps those times
        # in a min-heap.
        self.min_schedule_item = ScheduleQueue()
        # Counter of registered executors with a finite destruct_time.
        # `destroy_active_entity` short-circuits when this is zero so
        # the per-tick scan over `active_obj_map` only runs when a
        # destruction is actually pending.
        self._destructs_pending = 0
        self.sim_init_time = datetime.datetime.now()
        self.simulation_mode = SimulationMode.SIMULATION_IDLE

        # External Interface
        self.input_event_queue = []
        self.output_event_queue = deque()
        self._output_event_callback = None

        # TIME Handling
        self.ex_mode = ex_mode
        self.snapshot_manager = snapshot_manager
        
        if snapshot_manager:
            self.exec_factory = snapshot_manager.get_snapshot_factory()
        else:
            self.exec_factory = ExecutorFactory()
        #Factory pattern to convert Model to ModelExecutor
        
        self.dmc = DefaultMessageCatcher("dc")
        #Model for handling uncaught messages
        self.register_entity(self.dmc)
        
    def get_global_time(self):
        """
        Retrieves the current global time.(simulation time)

        Returns:
            float: The current global time
        """
        return self.global_time
    
    '''
    def set_snapshot_manager(self, snapshot_manager):
        """
        Sets the snapshot manager.

        Args:
            snapshot_manager (ModelSnapshotManager): The snapshot manager to set
        """
        self.snapshot_manager = snapshot_manager
    '''
    
    def register_entity(self, entity, inst_t=0, dest_t=Infinite, ename="default"):
        """
        Register simulation entity(Model).

        Args:
            entity (BehaviorModel or StructuralModel): The entity to register
            inst_t (float, optional): Instance creation time
            dest_t (float, optional): Destruction time
            ename (str, optional): SysExecutor name
        """

        sim_obj = self.exec_factory.create_executor(
            self.global_time, inst_t, self.global_time + dest_t, ename, entity, self
        )
        self.product_port_map[entity] = sim_obj

        # Avoid scanning active entities when none has a finite destruction
        # time.
        if dest_t < Infinite:
            self._destructs_pending += 1

        if sim_obj.get_create_time() not in self.waiting_obj_map:
            self.waiting_obj_map[sim_obj.get_create_time()] = []
            heapq.heappush(self._waiting_keys, sim_obj.get_create_time())

        self.waiting_obj_map[sim_obj.get_create_time()].append(sim_obj)

        if sim_obj.get_name() in self.model_map:
            self.model_map[sim_obj.get_name()].append(sim_obj)
        else:
            self.model_map[sim_obj.get_name()] = [sim_obj]
        
        

    def get_entity(self, model_name):
        """
        Retrieves entities by model name.

        Args:
            model_name (str): The name of the model

        Returns:
            list: List of entities
        """
        if model_name in self.model_map:
            return self.model_map[model_name]
        return []
    
    def get_model(self, name):
        """
        Retrieve Model by name.

        Args:
            name (str): The name of the model

        Returns:
            CoreModel: Model(BehaviorModel or StructuralModel)
        """
        return self.model_map[name][0].get_core_model()

    def remove_entity(self, model_name):
        """
        Removes an entity by model name.

        Args:
            model_name (str): The name of the model
        """
        if model_name in self.model_map:
            self.destory_entity(self.model_map[model_name])
            del self.model_map[model_name]

    def create_entity(self):
        """
        Creates entities that are scheduled for creation.
        """
        if self._waiting_keys:
            key = self._waiting_keys[0]
            if key <= self.global_time:
                heapq.heappop(self._waiting_keys)
                lst = self.waiting_obj_map.pop(key)
                for obj in lst:
                    self.active_obj_map[obj.get_obj_id()] = obj
                    obj.set_req_time(self.global_time)
                    self.min_schedule_item.push(obj)

    def destory_entity(self, delete_lst):
        """
        Destroys a list of entities.

        Args:
            delete_lst (list): List of entities to delete
        """
        for agent in delete_lst:
            del self.active_obj_map[agent.get_obj_id()]

            port_del_map = {}
            for key, value in self.port_map.items():
                if key[0] == agent:
                    port_del_map[key] = True

                if value:
                    del_items = []
                    for src_port in value:
                        src, _ = src_port
                        if src == agent:
                            del_items.append(src_port)
                    for item in del_items:
                        value.remove(item)

            for key in port_del_map:
                del self.port_map[key]

            self.min_schedule_item.remove(agent)

    def destroy_active_entity(self):
        """
        Destroys active entities whose ``destruct_time`` has elapsed.

        Fast-path: when no registered executor was ever given a finite
        ``destruct_time`` the scan is skipped entirely. This is the
        common case (most simulations register entities with the
        default ``Infinite`` destruct time) and the scan would
        otherwise run once per simulated tick.
        """
        if self._destructs_pending == 0:
            return
        if not self.active_obj_map:
            return

        delete_lst = []
        global_time = self.global_time
        for agent in self.active_obj_map.values():
            if agent._cached_destruct_time <= global_time:
                delete_lst.append(agent)

        if delete_lst:
            self._destructs_pending -= len(delete_lst)
            self.destory_entity(delete_lst)

    def coupling_relation(self, src_obj, out_port, dst_obj, in_port):
        """
        Related Model's input/output ports to each other. 
        Related src_obj's output port to dst_obj's input port.

        Args:
            src_obj (BehaviorMdoel or StructuralModel): Model to relate as output ports 
            out_port (str): src_obj's output port
            dst_obj (CoreModel): Model to relate as input ports 
            in_port (str): dst_obj's input port
        """
        if src_obj and src_obj != self:
            src_obj = self.product_port_map[src_obj]
        else:
            src_obj = self

        if dst_obj and dst_obj != self:
            dst_obj = self.product_port_map[dst_obj]
        else:
            dst_obj = self

        if (src_obj, out_port) in self.port_map:
            self.port_map[(src_obj, out_port)].append((dst_obj, in_port))
        else:
            self.port_map[(src_obj, out_port)] = [(dst_obj, in_port)]

    def get_relation(self):
        """
        Retrieves the current coupling relations.

        Returns:
            dict: The relation map
        """
        relation_map = {}
        for relation in self.port_map.keys():
            result_out_list = [] 
            in_tuple = (relation[0].get_core_model(), relation[1])
            out_list = self.port_map[relation]
            for out in out_list:
                result_out_list.append((out[0].get_core_model(), out[1]))
            relation_map[in_tuple] = result_out_list
        return relation_map
        
    def remove_relation(self, src, out_port, dst, in_port):
        """
        Removes a coupling relation.

        Args:
            src_obj (str): BehaviorMdoel or StructuralModel name, Models that remove relationships as output port
            out_port (str): src_obj's output port
            dst_obj (CoreModel): Models that remove relationships as input port
            in_port (str): dst_obj's input port
        """
        in_tuple = (self.model_map[src][0], out_port)
        found = self.port_map[in_tuple].index((self.model_map[dst][0], in_port))
        del self.port_map[in_tuple][found]
        
        if self.port_map[in_tuple] == []:
            del self.port_map[in_tuple]

    def reset_relation(self):
        """Resets all coupling relations."""
        self.port_map = {}

    def single_output_handling(self, obj, msg):
        """Immediate (non-two-phase) delivery of a single message.

        .. deprecated::
            This method applies ``ext_trans`` immediately and cannot form a
            confluent transition. Use ``insert_external_event`` and the normal
            simulation tick for new code.

        The receiver is rescheduled after delivery so that its updated request
        time is visible to ``ScheduleQueue``.

        Uncoupled emits are dropped silently unless the executor was
        built with ``track_uncaught=True``, in which case they fall back
        to ``self.dmc`` (the previous default behaviour).

        Args:
            obj: source executor
            msg (SysMessage): the message
        """
        for destination in self._destinations_for(obj, msg.get_dst()):
            if destination[0] is self:
                with self.condition:
                    self.output_event_queue.append((self.global_time, msg.retrieve()))
                if self._output_event_callback:
                    self._output_event_callback()
            elif destination[0].get_obj_id() in self.active_obj_map:
                destination[0].ext_trans(destination[1], msg)
                destination[0].set_req_time(self.global_time)
                self.min_schedule_item.push(destination[0])

    def output_handling(self, obj, msg_deliver):
        """
        Handles output messages.

        Output values are propagated by reference. Multiple subscribers to a
        port receive the same ``SysMessage`` object, so a receiver that needs
        to mutate a payload should copy it first.

        Args:
            obj (BehaviorModel or StructuralModel): Model
            msg_deliver (MessageDeliverer): batched output messages from `obj`
        """
        if msg_deliver.has_contents():
            for msg in msg_deliver.get_contents():
                self.single_output_handling(obj, msg)

    def init_sim(self):
        """Initializes the simulation."""
        self.simulation_mode = SimulationMode.SIMULATION_RUNNING
        
        if self.active_obj_map is None:
            self.global_time = min(self.waiting_obj_map)

        if not self.min_schedule_item:
            for obj in self.active_obj_map.items():
                if obj[1].time_advance() < 0:
                    print("You should give positive real number for the deadline")
                    raise AssertionError

                obj[1].set_req_time(self.global_time)
                self.min_schedule_item.push(obj[1])

    def _peek_next_event_time(self):
        """Smallest scheduled time across the FEL, external-event queue,
        and waiting-creation queue. Returns ``Infinite`` if nothing is
        pending.
        """
        next_t = (
            self.min_schedule_item.peek_time(default=Infinite)
            if self.min_schedule_item
            else Infinite
        )
        if self.input_event_queue:
            ext_t = self.input_event_queue[0][0]
            if ext_t < next_t:
                next_t = ext_t
        if self._waiting_keys:
            wait_t = self._waiting_keys[0]
            if wait_t < next_t:
                next_t = wait_t
        return next_t

    _NO_DESTINATIONS = ()

    def _destinations_for(self, src_executor, src_port):
        """Return ``(dst_executor, dst_port)`` pairs for a source emit.

        Behaviour depends on ``track_uncaught``:

        * Default (``track_uncaught=False``): uncoupled ports return an
          empty tuple.
        * Debug (``track_uncaught=True``): uncoupled ports get a lazily
          installed fallback to ``self.dmc``.
        """
        pair = (src_executor, src_port)
        coupling = self.port_map.get(pair)
        if coupling is not None:
            return coupling
        if self._track_uncaught:
            self.port_map[pair] = fallback = [
                (self.active_obj_map[self.dmc.get_obj_id()], "uncaught")
            ]
            return fallback
        return self._NO_DESTINATIONS

    def _run_instant(self, instant, imminent):
        """Process all model activity at one simulated instant.

        ``schedule`` and ``step`` both use this method. Outputs are collected
        before transitions, and external events due at ``instant`` share the
        same input bag as coupled model output.

        Phases:
          * A: collect ``output()`` from every imminent model.
          * B: route outputs through coupling into a per-receiver bag,
            already seeded with external events due at ``<= instant``.
          * C: dispatch the transition for each affected model:
            imminent + receiving -> ``con_trans``; imminent only ->
            ``int_trans``; receiving only -> ``ext_trans``.
          * D: reschedule every affected model.

        Args:
            instant (float): simulated time of this tick. ``global_time``
                must already equal ``instant``.
            imminent (list): executors already popped for ``instant``.
                May be empty when only external events are due.
        """
        active_obj_map = self.active_obj_map
        callback = self._output_event_callback
        output_queue = self.output_event_queue

        # Start each receiver's input bag with external events due now.
        influenced_inputs = {}      # dst_executor -> list[(dst_port, msg)]
        if self.input_event_queue:
            with self.condition:
                while (self.input_event_queue
                       and self.input_event_queue[0][0] <= instant):
                    _, ext_msg = heapq.heappop(self.input_event_queue)
                    for dst_exec, dst_port in self._destinations_for(
                        self, ext_msg.get_dst()
                    ):
                        if dst_exec is not self and dst_exec._obj_id in active_obj_map:
                            influenced_inputs.setdefault(
                                dst_exec, []
                            ).append((dst_port, ext_msg))

        if not imminent and not influenced_inputs:
            return

        # Phase A: collect output from imminent models.
        outputs = []
        for X in imminent:
            md = MessageDeliverer()
            X.output(md)
            if md.has_contents():
                outputs.append((X, md))

        # Phase B: route outputs through coupling, merging into the bag
        # already seeded with external events.
        for X, md in outputs:
            for msg in md.get_contents():
                for dst_exec, dst_port in self._destinations_for(X, msg.get_dst()):
                    if dst_exec is self:
                        # Output of the top-level simulator. The callback path
                        # uses the condition because another thread may wait.
                        if callback is not None:
                            with self.condition:
                                output_queue.append((instant, msg))
                            callback()
                        else:
                            output_queue.append((instant, msg))
                    elif dst_exec._obj_id in active_obj_map:
                        influenced_inputs.setdefault(
                            dst_exec, []
                        ).append((dst_port, msg))

        imminent_set = set(imminent)
        affected = imminent_set | set(influenced_inputs)

        # Phase C: apply a transition to every affected model.
        for M in affected:
            bag = influenced_inputs.get(M, ())
            is_imminent = M in imminent_set
            if is_imminent and bag:
                M.con_trans(bag)
            elif is_imminent:
                M.int_trans()
            else:
                for port, msg in bag:
                    M.ext_trans(port, msg)

        # Phase D: record each affected model's new request time.
        for M in affected:
            M.set_req_time(instant)
            self.min_schedule_item.push(M)

    def schedule(self):
        """Run one simulated-instant tick (V_TIME / R_TIME).

        :meth:`_run_instant` handles model activity. This method then advances
        time according to the execution mode:

          * V_TIME: jump ``global_time`` to ``min(next_event, target_time)``.
            If more events are still due at the current instant the
            timestamp is left unchanged so the next ``schedule()`` call
            processes them in another round at the same simulated time.
          * R_TIME: step by ``time_resolution`` and sleep to match
            wall-clock pace.
        """
        self.create_entity()

        # Only real-time execution needs a wall-clock duration.
        is_realtime = self.ex_mode == ExecutionType.R_TIME
        before = time.perf_counter() if is_realtime else None

        # Collect all request-time buckets that are already due. More than one
        # timestamp can be due after a paused simulation resumes.
        imminent = []
        fel = self.min_schedule_item
        while fel:
            next_t = fel.peek_time(default=Infinite)
            if next_t > self.global_time:
                break
            imminent.extend(fel.pop_all_at(next_t))

        # Include external events due at this instant in the same transition.
        self._run_instant(self.global_time, imminent)

        # Advance simulated time. External-event producers lock their queue
        # updates separately.
        if self.ex_mode == ExecutionType.V_TIME:
            next_t = self._peek_next_event_time()
            new_time = min(next_t, self.target_time)
            # A same-time event is processed by the next schedule call.
            if new_time > self.global_time:
                self.global_time = new_time
        elif self.ex_mode != ExecutionType.HLA_TIME:
            self.global_time += self.time_resolution

        self.destroy_active_entity()

        if is_realtime:
            delta = float(self.time_resolution) - float(time.perf_counter() - before)
            if delta > 0:
                time.sleep(delta)

    def simulate(self, _time=Infinite, _tm=True):
        """
        Runs the simulation for a given amount of time.

        Args:
            _time (float): The simulation time
            _tm (bool): Whether to use the termination manager 
        """
        if _tm:
            self.tm = TerminationManager(self)

        self.target_time = self.global_time + _time

        self.init_sim()

        # An unbounded virtual-time run stops when all remaining events are at
        # Infinite. A finite run stops at target_time.
        unbounded = (_time == Infinite)
        v_time = self.ex_mode == ExecutionType.V_TIME

        while self.global_time < self.target_time:
            # Acquire the condition only while paused; resume_sim notifies it.
            if self.simulation_mode == SimulationMode.SIMULATION_PAUSE:
                with self.condition:
                    while self.simulation_mode == SimulationMode.SIMULATION_PAUSE:
                        self.condition.wait()

            if self.simulation_mode == SimulationMode.SIMULATION_TERMINATED:
                break

            if (unbounded
                    and v_time
                    and not self.waiting_obj_map
                    and self.min_schedule_item
                    and self.min_schedule_item.peek_time(default=Infinite) == Infinite):
                self.simulation_mode = SimulationMode.SIMULATION_TERMINATED
                break

            self.schedule()

    def get_next_event_time(self):
        """
        Returns the next scheduled event time.
        Used by HLA federate to determine Time Advance Request value.

        Returns:
            float: The next event time, or Infinite if no events are scheduled
        """
        next_internal = Infinite
        if self.min_schedule_item:
            next_internal = self.min_schedule_item.peek_time(default=Infinite)

        next_external = Infinite
        with self.condition:
            if self.input_event_queue:
                next_external = self.input_event_queue[0][0]

        return min(next_internal, next_external)

    def step(self, granted_time):
        """
        Run one RTI-granted simulation step. Process every event whose
        ``req_time <= granted_time`` with the same instant-processing method
        used by ``schedule``.

        Multiple rounds may run at the same simulated instant when
        cascading sigma=0 transitions chain through the model graph;
        the outer ``while`` loop continues until no imminent remains
        within the granted window.

        Args:
            granted_time (float): time granted by the RTI.

        Returns:
            deque: output events generated and drained during this step.
        """
        self.create_entity()

        # Advance to each due event time without crossing the grant. Events
        # beyond the grant remain queued for a later call.
        while self.min_schedule_item or self.input_event_queue:
            next_internal = self.min_schedule_item.peek_time(default=Infinite)
            next_external = (self.input_event_queue[0][0]
                             if self.input_event_queue else Infinite)
            next_t = min(next_internal, next_external)
            if next_t > granted_time:
                break
            if next_t > self.global_time:
                self.global_time = next_t

            # _run_instant also includes external events due at next_t.
            imminent = self.min_schedule_item.pop_all_at(next_t)
            self._run_instant(next_t, imminent)

        # A successful grant sets the federate's logical time to the grant.
        if granted_time > self.global_time:
            self.global_time = granted_time

        self.destroy_active_entity()

        return self.handle_external_output_event()

    def pause_sim(self):
        """Pauses the simulation. External threads can still insert events while paused."""
        with self.condition:
            self.simulation_mode = SimulationMode.SIMULATION_PAUSE

    def resume_sim(self):
        """Resumes the simulation from a paused state."""
        with self.condition:
            self.simulation_mode = SimulationMode.SIMULATION_RUNNING
            self.condition.notify_all()

    def simulation_stop(self):
        """Stops the simulation and resets SysExecutor."""
        self.global_time = 0
        self.target_time = 0
        self.time_resolution = 1

        self.waiting_obj_map = {}
        self._waiting_keys = []
        self.active_obj_map = {}
        self.port_map = {}

        self.min_schedule_item = ScheduleQueue()
        self._destructs_pending = 0

        self.sim_init_time = datetime.datetime.now()

        self.dmc = DefaultMessageCatcher("dc")
        self.register_entity(self.dmc)

    def insert_external_event(self, _port, _msg, scheduled_time=0):
        """
        Inserts an external event into the simulation.
        
        Args:
            _port (str): port name
            _msg (SysMessage or None): Event message
            scheduled_time (float, optional): The scheduled time for the event
        """
        sys_msg = SysMessage("SRC", _port)
        sys_msg.insert(_msg)

        if _port in self.external_input_ports:
            with self.condition:
                heapq.heappush(
                    self.input_event_queue, (scheduled_time + self.global_time, sys_msg)
                )
        else:
            print("[INSERT_EXTERNAL_EVNT] Port Not Found")

    def insert_custom_external_event(self, _port, _bodylist, scheduled_time=0):
        """
        Inserts a custom external event into the simulation.

        Args:
            _port (str): The port name / 포트 이름
            _bodylist (list): The list of message bodies
            scheduled_time (float, optional): The scheduled time for the event
        """
        sys_msg = SysMessage("SRC", _port)
        sys_msg.extend(_bodylist)

        if _port in self.external_input_ports:
            with self.condition:
                heapq.heappush(
                    self.input_event_queue, (scheduled_time + self.global_time, sys_msg)
                )
        else:
            print("[INSERT_EXTERNAL_EVNT] Port Not Found")

    def set_output_event_callback(self, callback):
        """
        Sets a callback to be invoked when an output event is generated.
        Useful for inter-instance event delivery without polling.

        Args:
            callback (callable): A callable with no arguments
        """
        self._output_event_callback = callback

    def get_generated_event(self):
        """
        Returns a snapshot of the generated events queue.

        Returns:
            deque: A copy of the generated events queue
        """
        with self.condition:
            return deque(self.output_event_queue)

    def handle_external_input_event(self):
        """Drain due external events and deliver them immediately.

        .. deprecated::
            ``schedule`` and ``step`` now integrate external events through
            :meth:`_run_instant`. This immediate-delivery method remains for
            compatibility with external callers.

        The queue is checked before allocating a ``MessageDeliverer``. An event
        added concurrently after that check is handled on the next tick.
        """
        if not self.input_event_queue:
            return

        with self.condition:
            events = []
            while self.input_event_queue and self.input_event_queue[0][0] <= self.global_time:
                _, msg = heapq.heappop(self.input_event_queue)
                events.append(msg)

        if not events:
            return

        msg_deliver = MessageDeliverer()
        msg_deliver.data_list = events

        # single_output_handling reschedules each receiver after delivery.
        self.output_handling(self, msg_deliver)

    def handle_external_output_event(self):
        """
        Handles external output events and clears the output event queue.
        Thread-safe: deepcopy and clear are performed atomically.

        Returns:
            deque: List of output events
        """
        with self.condition:
            event_lists = copy.deepcopy(self.output_event_queue)
            self.output_event_queue.clear()
        return event_lists

    def is_terminated(self):
        """
        Checks if the simulation is terminated.
        
        Returns:
            bool: True if terminated, False otherwise
        """
        return self.simulation_mode == SimulationMode.SIMULATION_TERMINATED
    
    def snapshot_simulation(self, name = "", directory_path=".") : 
        """
        Snapshot the model and its releases. 

        Args : 
            name(str) : Name of the simulation to be snapshot
            directory_path : Where the simulation will be snapshot
            
        Raises:
            ValueError: Snapshot manager is not set.
        """
        if not self.snapshot_manager : 
            raise ValueError("Snapshot manager is not set. Cannot take snapshot.")
        
        if name == "" :
            name = self.get_name()
        
        self.snapshot_manager.snapshot_simulation(self.port_map, self.model_map, name, directory_path)
        
    def terminate_simulation(self):
        """Gracefully terminates the simulation."""
        with self.condition:
            self.simulation_mode = SimulationMode.SIMULATION_TERMINATED
            self.condition.notify_all()
