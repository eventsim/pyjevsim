"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT. The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Bank Simulation with Design of Experiments (DoE).

This example demonstrates how to use DoEManager to run multiple
replications of a simulation and collect statistical results.

Usage:
    python banksim_doe.py
"""

import statistics
import sys
import contexts

from pyjevsim.doe_manager import DoEManager
from pyjevsim.termination_condition import TimeBasedTermination
from pyjevsim.system_executor import SysExecutor

from model.model_accountant import BankAccountant
from model.model_queue import BankQueue
from model.model_user_gen import BankUserGenerator
from model.model_result import BankResult


class BankSimDoE(DoEManager):
    """Design of Experiments for Bank Simulation."""

    def __init__(self, num_replications: int, sim_time: float,
                 gen_num: int = 3, queue_size: int = 10, proc_num: int = 2):
        """
        Initialize Bank Simulation DoE.

        Args:
            num_replications (int): Number of simulation runs
            sim_time (float): Simulation time for each run
            gen_num (int): Number of user generators
            queue_size (int): Queue capacity
            proc_num (int): Number of accountants
        """
        termination = TimeBasedTermination(sim_time)
        super().__init__(
            num_replications=num_replications,
            termination_condition=termination,
            time_resolution=1.0
        )

        self.sim_time = sim_time
        self.gen_num = gen_num
        self.queue_size = queue_size
        self.proc_num = proc_num

    def setup_models(self, executor: SysExecutor, replication_idx: int):
        """
        Setup bank simulation models.

        Args:
            executor (SysExecutor): The simulation executor
            replication_idx (int): Current replication number
        """
        # Create generators
        gen_list = []
        for i in range(self.gen_num):
            gen = BankUserGenerator(f'gen{i}')
            gen_list.append(gen)
            executor.register_entity(gen)

        # Create queue
        queue = BankQueue('Queue', self.queue_size, self.proc_num)
        executor.register_entity(queue)

        # Create accountants
        account_list = []
        for i in range(self.proc_num):
            account = BankAccountant('BankAccountant', i)
            account_list.append(account)
            executor.register_entity(account)

        # Create result collector
        result = BankResult('result', max_user=1000)
        executor.register_entity(result)

        # Setup couplings
        executor.insert_input_port('start')

        for gen in gen_list:
            executor.coupling_relation(None, 'start', gen, 'start')
            executor.coupling_relation(gen, 'user_out', queue, 'user_in')

        executor.coupling_relation(queue, "result", result, "drop")

        for i in range(self.proc_num):
            executor.coupling_relation(queue, f'proc{i}', account_list[i], 'in')
            executor.coupling_relation(account_list[i], 'next', queue, 'proc_checked')
            executor.coupling_relation(account_list[i], 'next', result, 'process')

        # Insert initial event
        executor.insert_external_event('start', None)

    def collect_data(self, executor: SysExecutor, replication_idx: int):
        """
        Collect data from completed simulation.

        Args:
            executor (SysExecutor): The simulation executor
            replication_idx (int): Current replication number

        Returns:
            dict: Collected data
        """
        queue_model = executor.get_model("Queue")
        result_model = executor.get_model("result")

        # Collect statistics
        total_generated = sum(
            executor.get_model(f"gen{i}").get_user()
            for i in range(self.gen_num)
        )

        return {
            "replication": replication_idx,
            "final_time": executor.get_global_time(),
            "total_generated": total_generated,
            "processed_users": result_model.user_count,
            "dropped_users": result_model.drop_user_count,
            "queue_length": len(queue_model.user)
        }

    def aggregate_results(self):
        """
        Aggregate results from all replications.

        Returns:
            dict: Aggregated statistics
        """
        processed = [d["processed_users"] for d in self.replication_data]
        dropped = [d["dropped_users"] for d in self.replication_data]
        generated = [d["total_generated"] for d in self.replication_data]

        return {
            "num_replications": self.num_replications,
            "configuration": {
                "sim_time": self.sim_time,
                "gen_num": self.gen_num,
                "queue_size": self.queue_size,
                "proc_num": self.proc_num
            },
            "statistics": {
                "processed": {
                    "mean": statistics.mean(processed),
                    "stdev": statistics.stdev(processed) if len(processed) > 1 else 0,
                    "min": min(processed),
                    "max": max(processed)
                },
                "dropped": {
                    "mean": statistics.mean(dropped),
                    "stdev": statistics.stdev(dropped) if len(dropped) > 1 else 0,
                    "min": min(dropped),
                    "max": max(dropped)
                },
                "generated": {
                    "mean": statistics.mean(generated),
                    "stdev": statistics.stdev(generated) if len(generated) > 1 else 0,
                    "min": min(generated),
                    "max": max(generated)
                }
            },
            "raw_data": self.replication_data
        }


if __name__ == "__main__":
    # Configuration
    num_replications = 10
    sim_time = 100
    gen_num = 3
    queue_size = 10
    proc_num = 2

    print("=" * 60)
    print("Bank Simulation - Design of Experiments")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Replications: {num_replications}")
    print(f"  Simulation Time: {sim_time}")
    print(f"  Generators: {gen_num}")
    print(f"  Queue Size: {queue_size}")
    print(f"  Processors: {proc_num}")
    print("=" * 60)

    # Run experiment
    doe = BankSimDoE(
        num_replications=num_replications,
        sim_time=sim_time,
        gen_num=gen_num,
        queue_size=queue_size,
        proc_num=proc_num
    )

    results = doe.run_experiment()

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    stats = results["statistics"]

    print(f"\nProcessed Users:")
    print(f"  Mean:  {stats['processed']['mean']:.2f}")
    print(f"  StDev: {stats['processed']['stdev']:.2f}")
    print(f"  Min:   {stats['processed']['min']}")
    print(f"  Max:   {stats['processed']['max']}")

    print(f"\nDropped Users:")
    print(f"  Mean:  {stats['dropped']['mean']:.2f}")
    print(f"  StDev: {stats['dropped']['stdev']:.2f}")
    print(f"  Min:   {stats['dropped']['min']}")
    print(f"  Max:   {stats['dropped']['max']}")

    print(f"\nGenerated Users:")
    print(f"  Mean:  {stats['generated']['mean']:.2f}")
    print(f"  StDev: {stats['generated']['stdev']:.2f}")
    print(f"  Min:   {stats['generated']['min']}")
    print(f"  Max:   {stats['generated']['max']}")

    print("\n" + "=" * 60)
    print("Individual Replication Results:")
    print("=" * 60)
    print(f"{'Rep':<5} {'Generated':<12} {'Processed':<12} {'Dropped':<10} {'Queue':<8}")
    print("-" * 60)

    for data in results["raw_data"]:
        print(f"{data['replication']:<5} "
              f"{data['total_generated']:<12} "
              f"{data['processed_users']:<12} "
              f"{data['dropped_users']:<10} "
              f"{data['queue_length']:<8}")

    print("=" * 60)
