"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Tests of the bank example in examples/banksim: opt-in seeding, the
order-independent queue and result models, the generator's stop port, the
result report and the what-if change of the runners.
"""

import io
import random
import types

import pytest

from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.executor import Executor
from pyjevsim.system_executor import SysExecutor

from examples.banksim.model import model_user_gen
from examples.banksim.model.model_accountant import BankAccountant
from examples.banksim.model.model_queue import BankQueue, OrderedBankQueue
from examples.banksim.model.model_result import BankResult, OrderedBankResult
from examples.banksim.model.model_user_gen import BankUser, BankUserGenerator
from examples.banksim.seeding import model_rng, stream_seed


def build_bank(seed, gen_num=6, queue_size=3, proc_num=3, max_user=10**9):
    """The banksim_classic.py topology, seeded, with the ordered models."""
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gens = []
    for i in range(gen_num):
        gen = BankUserGenerator(f"gen{i}", rng=model_rng(seed, f"gen{i}"))
        gens.append(gen)
        ss.register_entity(gen)
    que = OrderedBankQueue("Queue", queue_size, proc_num)
    ss.register_entity(que)
    accountants = []
    for i in range(proc_num):
        acc = BankAccountant(f"processor{i}", i)
        accountants.append(acc)
        ss.register_entity(acc)
    result = OrderedBankResult("result", max_user)
    ss.register_entity(result)

    ss.insert_input_port("start")
    for gen in gens:
        ss.coupling_relation(None, "start", gen, "start")
        ss.coupling_relation(gen, "user_out", que, "user_in")
    ss.coupling_relation(que, "result", result, "drop")
    for i in range(proc_num):
        ss.coupling_relation(que, f"proc{i}", accountants[i], "in")
        ss.coupling_relation(accountants[i], "next", que, "proc_checked")
        ss.coupling_relation(accountants[i], "next", result, "process")
    ss.insert_external_event("start", None)
    return ss, gens, que, result


def outcome(gens, que, result):
    return {
        "generated": [g.generated_user for g in gens],
        "served": [(p, str(u)) for p, u in result.user],
        "dropped": sorted(str(u) for u in result.drop_user),
        "queue": [str(u) for u in que.user],
    }


def run_bank(seed, ticks=400, salt=None, monkeypatch=None):
    if salt is not None:
        # Change the engine's same-instant processing order (set iteration
        # follows the executors' hashes), as the trace oracle does.
        monkeypatch.setattr(Executor, "__hash__",
                            lambda self: hash((salt, self.get_obj_id())))
    ss, gens, que, result = build_bank(seed)
    for _ in range(ticks):
        ss.simulate(1)
    return outcome(gens, que, result)


def test_same_seed_same_run_in_any_same_instant_order(monkeypatch):
    first = run_bank(7)
    assert first["served"] and first["dropped"]
    assert run_bank(7) == first
    for salt in (1, 2, 3):
        assert run_bank(7, salt=salt, monkeypatch=monkeypatch) == first


def test_different_seeds_differ():
    a, b = run_bank(7), run_bank(8)
    assert a["generated"] != b["generated"]
    assert a["served"] != b["served"]


def test_streams_depend_on_seed_and_name_only():
    assert stream_seed(1, "gen0") == stream_seed(1, "gen0")
    assert len({stream_seed(1, "gen0"), stream_seed(1, "gen1"), stream_seed(2, "gen0")}) == 3
    assert model_rng(None, "gen0") is None
    assert model_rng(5, "gen3").random() == random.Random(stream_seed(5, "gen3")).random()


def test_generator_without_rng_draws_from_module_random(monkeypatch):
    calls = []

    class Recorder:
        def randint(self, a, b):
            calls.append((a, b))
            return 4

    monkeypatch.setattr(model_user_gen, "random", Recorder())
    gen = BankUserGenerator("gen0")
    assert calls == [(1, 10)]
    assert gen._states["GEN"] == 4.0
    # no instance attribute for the default stream: state and pickles as before
    assert "_rng" not in vars(gen)

    seeded = BankUserGenerator("gen1", rng=random.Random(3))
    assert calls == [(1, 10)]
    assert vars(seeded)["_rng"] is not None


def test_runner_defaults_keep_the_original_models():
    pytest.importorskip("yaml")
    from examples.banksim.runner import bank_classes
    assert bank_classes(None) == (BankQueue, BankResult)
    assert bank_classes(0) == (OrderedBankQueue, OrderedBankResult)


def _single_generator(seed=1):
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen = BankUserGenerator("gen0", rng=random.Random(seed))
    ss.register_entity(gen)
    for port in ("start", "stop"):
        ss.insert_input_port(port)
        ss.coupling_relation(None, port, gen, port)
    ss.insert_external_event("start", None)
    return ss, gen


def test_generator_stops_on_stop_port_and_restarts():
    assert "stop" in BankUserGenerator("g").retrieve_input_ports()
    ss, gen = _single_generator()
    ss.simulate(50)
    running = gen.generated_user
    assert running > 0

    ss.insert_external_event("stop", None)
    ss.simulate(1)
    stopped = gen.generated_user
    assert gen._cur_state == "WAIT"
    assert ss.get_next_event_time() == Infinite
    ss.simulate(200)
    assert gen.generated_user == stopped <= running + 1

    ss.insert_external_event("start", None)
    ss.simulate(50)
    assert gen.generated_user > stopped


def _reference_report(result):
    """The report as the former one-print-per-line get_result wrote it."""
    out = io.StringIO()
    print("[BANKSIM RESULT]", file=out)
    print("- Accountant user : ", result.user_count, file=out)
    print("- Dropped user : ", result.drop_user_count, file=out)
    print("\n [Accountant user list]", file=out)
    for p, u in result.user:
        print(p, u.__str__(), file=out)
    print("\n [Dropped user list]", file=out)
    for d in result.drop_user:
        print(d.__str__(), file=out)
    return out.getvalue()


@pytest.mark.parametrize("n_users", [0, 3, 70000])
def test_result_report_text_is_unchanged(monkeypatch, n_users):
    result = BankResult("result", 10)
    for k in range(n_users):
        u = BankUser(f"gen{k % 3}-{k}", k % 10 + 1)
        u.set_arrival_time(float(k))
        u.calc_wait_time(float(k + 5))
        result.user.append((f"proc{k % 4}", u))
        if k % 2:
            result.drop_user.append(BankUser(f"gen{k % 3}-d{k}", 2))
    result.user_count = len(result.user)
    result.drop_user_count = len(result.drop_user)

    sink = io.StringIO()
    flushes = []
    sink.flush = lambda: flushes.append(sink.tell())
    monkeypatch.setattr("sys.stdout", sink)
    result.get_result()
    assert sink.getvalue() == _reference_report(result)
    # flushed once, after everything was written
    assert flushes == [len(sink.getvalue())]


def test_ordered_result_stops_at_max_user(monkeypatch):
    from examples.banksim.model import model_result

    class Stop(Exception):
        pass

    def _exit(code=0):
        raise Stop(code)

    shim = types.SimpleNamespace(_exit=_exit)
    monkeypatch.setattr(model_result, "os", shim)
    monkeypatch.setattr("sys.stdout", io.StringIO())
    ss, gens, que, result = build_bank(3, max_user=40)
    with pytest.raises(Stop):
        for _ in range(1000):
            ss.simulate(1)
    assert result.user_count == 40
    assert len(result.user) == 40


def _what_if_bank(gen_num, wiq_gen_num, seed=4):
    from examples.banksim.runner import apply_what_if
    ss, gens, que, result = build_bank(seed, gen_num=gen_num)
    for _ in range(30):
        ss.simulate(1)
    apply_what_if(ss, gen_num, wiq_gen_num, que, seed)
    before = {name: ss.get_model(name).generated_user for name in ss.model_map
              if name.startswith("gen")}
    for _ in range(100):
        ss.simulate(1)
    after = {name: ss.get_model(name).generated_user for name in ss.model_map
             if name.startswith("gen")}
    return before, after


def test_what_if_fewer_generators_stops_the_last_ones():
    pytest.importorskip("yaml")
    before, after = _what_if_bank(6, 4)
    assert sorted(after) == [f"gen{i}" for i in range(6)]
    for i in range(6):
        grew = after[f"gen{i}"] - before[f"gen{i}"]
        if i < 4:
            assert grew > 5
        else:
            assert grew <= 1   # at most the user due at the instant of the stop


def test_what_if_more_generators_adds_new_names():
    pytest.importorskip("yaml")
    before, after = _what_if_bank(4, 6)
    assert sorted(before) == sorted(after) == sorted(f"gen{i}" for i in range(6))
    assert before["gen4"] == before["gen5"] == 0
    assert after["gen4"] > 0 and after["gen5"] > 0
