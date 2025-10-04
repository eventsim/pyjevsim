"""
Performance profiling script for pyjevsim simulation execution.
This script measures execution time, memory usage, and identifies performance bottlenecks.

Usage:
    python performance_profiling.py
"""

import cProfile
import pstats
import io
import time
import tracemalloc
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor
from examples.banksim.model.model_accountant import BankAccountant
from examples.banksim.model.model_queue import BankQueue
from examples.banksim.model.model_user_gen import BankUserGenerator
from examples.banksim.model.model_result import BankResult


def setup_banksim(gen_num=3, queue_size=10, proc_num=5, max_user=300):
    """Setup bank simulation with given parameters."""
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)

    # Create and register user generators
    gen_list = []
    for i in range(gen_num):
        gen = BankUserGenerator(f'gen{i}')
        gen_list.append(gen)
        ss.register_entity(gen)

    # Create and register queue
    que = BankQueue('Queue', queue_size, proc_num)
    ss.register_entity(que)

    # Create and register accountants
    account_list = []
    for i in range(proc_num):
        account = BankAccountant('BankAccountant', i)
        account_list.append(account)
        ss.register_entity(account)

    # Create and register result collector
    result = BankResult('result', max_user)
    ss.register_entity(result)

    # Setup coupling relations
    ss.insert_input_port('start')
    for gen in gen_list:
        ss.coupling_relation(None, 'start', gen, 'start')
        ss.coupling_relation(gen, 'user_out', que, 'user_in')
    ss.coupling_relation(que, "result", result, "drop")
    for i in range(proc_num):
        ss.coupling_relation(que, f'proc{i}', account_list[i], 'in')
        ss.coupling_relation(account_list[i], 'next', que, 'proc_checked')
        ss.coupling_relation(account_list[i], 'next', result, 'process')

    ss.insert_external_event('start', None)

    return ss


def run_simulation(ss, sim_time=1000):
    """Run simulation for specified time."""
    ss.simulate(sim_time)


def profile_execution_time(scenarios):
    """Profile execution time for different scenarios."""
    print("=" * 80)
    print("EXECUTION TIME PROFILING")
    print("=" * 80)

    results = []
    for name, params in scenarios.items():
        print(f"\nScenario: {name}")
        print(f"  Parameters: {params}")

        # Setup simulation
        start_setup = time.perf_counter()
        ss = setup_banksim(**params['setup'])
        setup_time = time.perf_counter() - start_setup

        # Run simulation
        start_sim = time.perf_counter()
        run_simulation(ss, params['sim_time'])
        sim_time = time.perf_counter() - start_sim

        total_time = setup_time + sim_time

        print(f"  Setup time:      {setup_time:.4f} seconds")
        print(f"  Simulation time: {sim_time:.4f} seconds")
        print(f"  Total time:      {total_time:.4f} seconds")

        results.append({
            'name': name,
            'setup_time': setup_time,
            'sim_time': sim_time,
            'total_time': total_time
        })

    return results


def profile_memory_usage(scenarios):
    """Profile memory usage for different scenarios."""
    print("\n" + "=" * 80)
    print("MEMORY USAGE PROFILING")
    print("=" * 80)

    results = []
    for name, params in scenarios.items():
        print(f"\nScenario: {name}")

        # Start memory tracking
        tracemalloc.start()

        # Setup and run simulation
        ss = setup_banksim(**params['setup'])
        current, peak = tracemalloc.get_traced_memory()
        setup_memory = current / 1024 / 1024  # Convert to MB

        run_simulation(ss, params['sim_time'])
        current, peak = tracemalloc.get_traced_memory()

        tracemalloc.stop()

        current_mb = current / 1024 / 1024
        peak_mb = peak / 1024 / 1024

        print(f"  Setup memory:   {setup_memory:.2f} MB")
        print(f"  Current memory: {current_mb:.2f} MB")
        print(f"  Peak memory:    {peak_mb:.2f} MB")

        results.append({
            'name': name,
            'setup_memory': setup_memory,
            'current_memory': current_mb,
            'peak_memory': peak_mb
        })

    return results


def profile_detailed_performance():
    """Detailed performance profiling using cProfile."""
    print("\n" + "=" * 80)
    print("DETAILED PERFORMANCE PROFILING (cProfile)")
    print("=" * 80)

    # Create profiler
    profiler = cProfile.Profile()

    # Setup simulation
    ss = setup_banksim(gen_num=3, queue_size=10, proc_num=5, max_user=300)

    # Profile simulation execution
    profiler.enable()
    run_simulation(ss, sim_time=1000)
    profiler.disable()

    # Print statistics
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')

    print("\nTop 20 functions by cumulative time:")
    ps.print_stats(20)
    print(s.getvalue())

    # Also sort by total time
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.strip_dirs()
    ps.sort_stats('tottime')

    print("\nTop 20 functions by total time:")
    ps.print_stats(20)
    print(s.getvalue())


def main():
    """Main function to run all profiling tests."""
    print("pyjevsim Performance Profiling")
    print("=" * 80)

    # Define test scenarios
    scenarios = {
        'Small': {
            'setup': {'gen_num': 2, 'queue_size': 5, 'proc_num': 3, 'max_user': 100},
            'sim_time': 500
        },
        'Medium': {
            'setup': {'gen_num': 3, 'queue_size': 10, 'proc_num': 5, 'max_user': 300},
            'sim_time': 1000
        },
        'Large': {
            'setup': {'gen_num': 5, 'queue_size': 20, 'proc_num': 10, 'max_user': 500},
            'sim_time': 2000
        }
    }

    # Run profiling tests
    time_results = profile_execution_time(scenarios)
    memory_results = profile_memory_usage(scenarios)

    # Detailed profiling on medium scenario
    profile_detailed_performance()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nExecution Time Summary:")
    print(f"{'Scenario':<15} {'Setup (s)':<15} {'Simulation (s)':<15} {'Total (s)':<15}")
    print("-" * 60)
    for result in time_results:
        print(f"{result['name']:<15} {result['setup_time']:<15.4f} {result['sim_time']:<15.4f} {result['total_time']:<15.4f}")

    print("\nMemory Usage Summary:")
    print(f"{'Scenario':<15} {'Setup (MB)':<15} {'Current (MB)':<15} {'Peak (MB)':<15}")
    print("-" * 60)
    for result in memory_results:
        print(f"{result['name']:<15} {result['setup_memory']:<15.2f} {result['current_memory']:<15.2f} {result['peak_memory']:<15.2f}")


if __name__ == "__main__":
    main()
