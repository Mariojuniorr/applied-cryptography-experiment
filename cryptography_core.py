# Mário Lúcio Santos Júnior - 12211BSI252
# Paulo Henrique Alves Teixeira - 12211BSI214
import uuid
import time
import os
import platform
import ctypes
import ctypes.wintypes
import random


# ******************************************** Estrutura SPN **********************************************

SBOX = {
    0b0000: 0b1110, 0b0001: 0b0100, 0b0010: 0b1101, 0b0011: 0b0001,
    0b0100: 0b0010, 0b0101: 0b1111, 0b0110: 0b1011, 0b0111: 0b1000,
    0b1000: 0b0011, 0b1001: 0b1010, 0b1010: 0b0110, 0b1011: 0b1100,
    0b1100: 0b0101, 0b1101: 0b1001, 0b1110: 0b0000, 0b1111: 0b0111
}

INV_SBOX = {v: k for k, v in SBOX.items()}


def permute(bits):
    n = len(bits)
    P = [(i * 5) % n for i in range(n)]
    return [bits[P[i]] for i in range(n)]


def inv_permute(bits):
    n = len(bits)
    P = [(i * 5) % n for i in range(n)]
    inv = [0] * n
    for i, p in enumerate(P):
        inv[p] = bits[i]
    return inv


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
    mac = uuid.getnode()

    cursor_entropy = 0
    if platform.system() == "Windows":
        try:
            pt = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            cursor_entropy = (pt.x << 16) ^ pt.y
        except:
            pass

    combined_int = (mac ^ cursor_entropy ^ os.getpid()) & 0xFFFFFFFF

    return [(combined_int >> i) & 1 for i in reversed(range(32))]


# ********************************************** Funções principais **********************************************
def GEN(seed_bits, rounds=16, block_size=128):
    x = seed_bits[:]  # copia

    keys = []

    for _ in range(rounds):
        sub = []

        for _ in range(block_size):
            # LFSR simples
            new_bit = x[0] ^ x[2] ^ x[5] ^ x[-1]

            sub.append(new_bit)

            x = x[1:] + [new_bit]

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


# ********************************************** TESTES **********************************************

def hamming(A, B):
    return sum(a ^ b for a, b in zip(A, B))


def test_avalanche_message(seed_bits, M, rounds=16):
    keys = GEN(seed_bits, rounds, len(M))
    C1 = ENC(keys, M)

    M2 = M[:]
    M2[0] ^= 1

    C2 = ENC(keys, M2)
    return hamming(C1, C2) / len(M)


def test_avalanche_key(seed_bits, M, rounds=16):
    keys1 = GEN(seed_bits, rounds, len(M))
    C1 = ENC(keys1, M)

    seed2 = seed_bits[:]
    seed2[0] ^= 1

    keys2 = GEN(seed2, rounds, len(M))
    C2 = ENC(keys2, M)

    return hamming(C1, C2) / len(M)


def test_balance(C):
    ones = sum(C)
    zeros = len(C) - ones
    return ones / len(C), zeros / len(C)


def run_tests(seed_bits, M, rounds=16):
    print("\n********TESTES*********")

    keys = GEN(seed_bits, rounds, len(M))

    start = time.perf_counter()
    C = ENC(keys, M)
    M2 = DEC(keys, C)
    end = time.perf_counter()

    print("Tempo ENC+DEC:", end - start)
    print("Correção:", M == M2)
    print("Difusão (Avalanche M):", test_avalanche_message(seed_bits, M, rounds))
    print("Confusão (Avalanche K):", test_avalanche_key(seed_bits, M, rounds))
    print("Balanceamento bits:", test_balance(C))


# ********************************************** MAIN **********************************************

if __name__ == "__main__":

    s_list = seed()

    MSG_SIZE = 128
    M = [random.randint(0, 1) for _ in range(MSG_SIZE)]

    keys = GEN(s_list, rounds=16, block_size=MSG_SIZE)

    C = ENC(keys, M)
    M_dec = DEC(keys, C)

    print("Seed (bits):", s_list)
    print("Mensagem original:", M)
    print("Cifrado:", C)
    print("Decifrado:", M_dec)

    run_tests(s_list, M)