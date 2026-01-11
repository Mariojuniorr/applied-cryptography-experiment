import uuid
import time
import os
import platform
import ctypes
import ctypes.wintypes

def GEN(seed: int) -> list[int]:
    seed_bits = bin(seed)[2:]
    size = 4 * len(seed_bits)

    K = []
    x = seed & 0xFFFFFFFF

    for _ in range(size):
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17)
        x ^= (x << 5) & 0xFFFFFFFF
        K.append(x & 1)

    return K

def ENC(K: list[int], M: list[int]) -> list[int]:
    assert len(K) == len(M)

    temp = [m ^ k for m, k in zip(M, K)]

    shift = sum(K) % len(K)
    return temp[shift:] + temp[:shift]


def DEC(K: list[int], C: list[int]) -> list[int]:
    assert len(K) == len(C)

    shift = sum(K) % len(K)

    temp = C[-shift:] + C[:-shift] if shift != 0 else C[:]

    return [t ^ k for t, k in zip(temp, K)]

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
    K = GEN(seed)

    M = [i % 2 for i in range(len(K))]

    start = time.perf_counter()
    C = ENC(K, M)
    M_dec = DEC(K, C)
    end = time.perf_counter()

    print("Seed:", seed)
    print("Key size:", len(K))
    print("Time dec and enc:", end - start, "seconds")
