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

        f = [((r & k) ^ ((r ^ k) & 1)) for r, k in zip(R, Ki)]

        newR = [l ^ fi for l, fi in zip(L, f)]
        L, R = newL, newR

    return L + R



def DEC(keys, C):
    n = len(C)
    L = C[:n//2]
    R = C[n//2:]

    for Ki in reversed(keys):
        newR = L

        f = [((l & k) ^ ((l ^ k) & 1)) for l, k in zip(L, Ki)]

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
    print("Correto?", M == M_dec)
    print("Tempo ENC+DEC:", end - start, "segundos")

