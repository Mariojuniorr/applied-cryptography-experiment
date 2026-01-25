import uuid
import time
import os
import platform
import ctypes
import ctypes.wintypes

def GEN(seed: int, rounds=16, block_size=64):
    x = seed & 0xFFFFFFFF
    keys = []

    for _ in range(rounds):
        sub = []
        for _ in range(block_size // 2):
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= (x >> 17)
            x ^= (x << 5) & 0xFFFFFFFF
            sub.append(x & 1)
        keys.append(sub)

    return keys

def ENC(keys, M):
    n = len(M)
    L = M[:n//2]
    R = M[n//2:]

    for Ki in keys:
        newL = R

        f = []
        for i, (r, k) in enumerate(zip(R, Ki)):
            left = R[i-1] if i > 0 else R[-1]
            right = R[(i+1) % len(R)]
            f.append((r ^ k ^ left ^ right) & 1)

        newR = [l ^ fi for l, fi in zip(L, f)]
        L, R = newL, newR

    return L + R



def DEC(keys, C):
    n = len(C)
    L = C[:n//2]
    R = C[n//2:]

    for Ki in reversed(keys):
        newR = L
        f = []
        for i, (r, k) in enumerate(zip(newR, Ki)):
            left = newR[i-1] if i > 0 else newR[-1]
            right = newR[(i+1) % len(newR)]
            f.append((r ^ k ^ left ^ right) & 1)

        newL = [r ^ fi for r, fi in zip(R, f)]
        L, R = newL, newR

    return L + R

def exotic_entropy_fast():
    # MAC address
    mac = uuid.getnode()

    # Posição do cursor
    cursor_entropy = 0
    if platform.system() == "Windows":
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        cursor_entropy = (pt.x << 16) ^ pt.y

    # Caos determinístico
    x = ((time.time_ns() ^ mac) & 0xFFFFFFFF) / (1 << 32)
    for _ in range(8):
        x = 3.99 * x * (1 - x)
    chaos_entropy = int(x * (1 << 32))

    return mac ^ cursor_entropy ^ chaos_entropy ^ os.getpid()



# **********************************************TESTES**********************************************

def hamming(A, B):
    return sum(a ^ b for a, b in zip(A, B))


def test_correctness(keys, M):
    C = ENC(keys, M)
    M2 = DEC(keys, C)
    return M == M2


def test_avalanche_message(seed, M, rounds=16):
    keys = GEN(seed, rounds, len(M))
    C1 = ENC(keys, M)

    # muda 1 bit da mensagem
    M2 = M[:]
    M2[0] ^= 1

    C2 = ENC(keys, M2)
    return hamming(C1, C2) / len(M)


def test_avalanche_key(seed, M, rounds=16):
    keys1 = GEN(seed, rounds, len(M))
    C1 = ENC(keys1, M)

    # muda 1 bit da seed
    seed2 = seed ^ 1
    keys2 = GEN(seed2, rounds, len(M))
    C2 = ENC(keys2, M)

    return hamming(C1, C2) / len(M)


def test_balance(C):
    ones = sum(C)
    zeros = len(C) - ones
    return ones / len(C), zeros / len(C)

def run_tests(seed, M, rounds=16):

    print("\n********TESTES*********")

    keys = GEN(seed, rounds, len(M))

    start = time.perf_counter()
    C = ENC(keys, M)
    M2 = DEC(keys, C)
    end = time.perf_counter()

    print("Tempo ENC+DEC:", end - start, "seconds")

    print("Correção:", M == M2)

    aval_m = test_avalanche_message(seed, M, rounds)
    print("Difusão (Avalanche M):", aval_m)

    aval_k = test_avalanche_key(seed, M, rounds)
    print("Confusão (Avalanche K):", aval_k)

    ones, zeros = test_balance(C)
    print("Balanceamento bits (1,0):", ones, zeros)


if __name__ == "__main__":

    N = 1000
    start = time.perf_counter()
    for _ in range(N):
        exotic_entropy_fast()
    end = time.perf_counter()

    print("Average entropy time:", (end - start) / N)

    seed = exotic_entropy_fast()

    M = [i % 2 for i in range(64)]

    keys = GEN(seed, rounds=16, block_size=len(M))

    start = time.perf_counter()
    C = ENC(keys, M)
    M_dec = DEC(keys, C)
    end = time.perf_counter()

    print("Seed:", seed)
    print("Mensagem original:", M)
    print("Cifrado:", C)
    print("Decifrado:", M_dec)

    run_tests(seed,M)