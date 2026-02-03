import time
import random
import statistics

from cryptography_core import (
    GEN, ENC, DEC,
    test_avalanche_message,
    test_avalanche_key,
    test_balance,
    exotic_entropy_fast
)

ROUNDS = 16
SEED_BITS = 32
MSG_SIZE = 4 * SEED_BITS   # 128 bits
N_RUNS = 1000


def run_experiment(n_runs=N_RUNS):
    times = []
    avalanche_m = []
    avalanche_k = []
    balance_ones = []
    balance_zeros = []
    correctness = []

    for _ in range(n_runs):
        seed = exotic_entropy_fast() & 0xFFFFFFFF
        M = [random.randint(0, 1) for _ in range(MSG_SIZE)]

        keys = GEN(seed, rounds=ROUNDS, block_size=MSG_SIZE)

        start = time.perf_counter()
        C = ENC(keys, M)
        M2 = DEC(keys, C)
        end = time.perf_counter()

        times.append(end - start)
        correctness.append(M == M2)

        avalanche_m.append(
            test_avalanche_message(seed, M, ROUNDS)
        )

        avalanche_k.append(
            test_avalanche_key(seed, M, ROUNDS)
        )

        ones, zeros = test_balance(C)
        balance_ones.append(ones)
        balance_zeros.append(zeros)

    return {
        "runs": n_runs,
        "avg_time": statistics.mean(times),
        "avg_avalanche_m": statistics.mean(avalanche_m),
        "avg_avalanche_k": statistics.mean(avalanche_k),
        "avg_balance_ones": statistics.mean(balance_ones),
        "avg_balance_zeros": statistics.mean(balance_zeros),
        "correct_rate": sum(correctness) / n_runs
    }


def print_report(results):
    print("\n========== RELATÓRIO CRIPTOGRÁFICO ==========")
    print(f"Execuções: {results['runs']}")
    print(f"Tempo médio ENC+DEC: {results['avg_time']:.6f} s")
    print(f"Correção: {results['correct_rate']*100:.1f}%")
    print(f"Difusão média (Avalanche M): {results['avg_avalanche_m']:.4f}")
    print(f"Confusão média (Avalanche K): {results['avg_avalanche_k']:.4f}")
    print(f"Balanceamento médio (1s): {results['avg_balance_ones']:.4f}")
    print(f"Balanceamento médio (0s): {results['avg_balance_zeros']:.4f}")
    print("============================================")


if __name__ == "__main__":
    results = run_experiment()
    print_report(results)
