import uuid
import time
import os
import platform
import ctypes
import ctypes.wintypes
import random

# ******************************************** Estrutura SPN **********************************************

# S-box (4 bits → 4 bits)

SBOX = {
    0b0000: 0b1110, 0b0001: 0b0100, 0b0010: 0b1101, 0b0011: 0b0001,
    0b0100: 0b0010, 0b0101: 0b1111, 0b0110: 0b1011, 0b0111: 0b1000,
    0b1000: 0b0011, 0b1001: 0b1010, 0b1010: 0b0110, 0b1011: 0b1100,
    0b1100: 0b0101, 0b1101: 0b1001, 0b1110: 0b0000, 0b1111: 0b0111
}

INV_SBOX = {v: k for k, v in SBOX.items()}


# Permutação simples (difusão)
def permute(bits):
    n = len(bits)
    P = [(i * 5) % n for i in range(n)]
    return [bits[P[i]] for i in range(n)]

def inv_permute(bits):
    n = len(bits)
    P = [(i * 5) % n for i in range(n)]
    inv = [0]*n
    for i, p in enumerate(P):
        inv[p] = bits[i]
    return inv

# Aplicação da S-box
def apply_sbox(bits):
    out = []
    for i in range(0, len(bits), 4):
        block = bits[i:i+4]
        v = int("".join(map(str, block)), 2)
        s = SBOX[v]
        out.extend([(s >> j) & 1 for j in reversed(range(4))])
    return out

def apply_inv_sbox(bits):
    out = []
    for i in range(0, len(bits), 4):
        block = bits[i:i+4]
        v = int("".join(map(str, block)), 2)
        s = INV_SBOX[v]
        out.extend([(s >> j) & 1 for j in reversed(range(4))])
    return out


# ********************************************** Geração da SEED **********************************************

def seed():
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


# ********************************************** Funções principais **********************************************

def GEN(seed: int, rounds=16, block_size=128):
    x = seed & 0xFFFFFFFF
    keys = []

    for _ in range(rounds):
        sub = []
        for _ in range(block_size):
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= (x >> 17)
            x ^= (x << 5) & 0xFFFFFFFF
            sub.append(x & 1)
        keys.append(sub)

    return keys

def ENC(keys, M):
    state = M[:]

    for i, Ki in enumerate(keys):
        state = [b ^ k for b, k in zip(state, Ki)]

        state = apply_sbox(state)

        if i != len(keys) - 1:
            state = permute(state)

    return state



def DEC(keys, C):
    state = C[:]

    for i, Ki in enumerate(reversed(keys)):
        if i != 0:
            state = inv_permute(state)

        state = apply_inv_sbox(state)

        state = [b ^ k for b, k in zip(state, Ki)]

    return state


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
        seed()
    end = time.perf_counter()

    print("Average entropy time:", (end - start) / N)

    seed = seed() & 0xFFFFFFFF
    SEED_BITS = 32
    MSG_SIZE = 4 * SEED_BITS  # 128 bits

    M = [random.randint(0, 1) for _ in range(MSG_SIZE)]

    keys = GEN(seed, rounds=16, block_size=MSG_SIZE)

    start = time.perf_counter()
    C = ENC(keys, M)
    M_dec = DEC(keys, C)
    end = time.perf_counter()

    print("Seed:", seed)
    print("Mensagem original:", M)
    print("Cifrado:", C)
    print("Decifrado:", M_dec)

    run_tests(seed,M)