# Mário Lúcio Santos Júnior - 12211BSI252
# Paulo Henrique Alves Teixeira - 12211BSI214
import uuid
import time
import os
import platform
import ctypes
import ctypes.wintypes
import random
from typing import List

# ******************************************** Estrutura SPN **********************************************

SBOX = {
    0b0000: 0b1110, 0b0001: 0b0100, 0b0010: 0b1101, 0b0011: 0b0001,
    0b0100: 0b0010, 0b0101: 0b1111, 0b0110: 0b1011, 0b0111: 0b1000,
    0b1000: 0b0011, 0b1001: 0b1010, 0b1010: 0b0110, 0b1011: 0b1100,
    0b1100: 0b0101, 0b1101: 0b1001, 0b1110: 0b0000, 0b1111: 0b0111
}

INV_SBOX = {v: k for k, v in SBOX.items()}

P_INDICES = [(i * 37) % 128 for i in range(128)]
INV_P_INDICES = [0] * 128
for i, p in enumerate(P_INDICES):
    INV_P_INDICES[p] = i

def permute(bits):
    n = len(bits)
    P = [(i * 37) % n for i in range(n)]
    return [bits[P[i]] for i in range(n)]


def inv_permute(bits):
    n = len(bits)
    P = [(i * 5) % n for i in range(n)]
    inv = [0] * n
    for i, p in enumerate(P):
        inv[p] = bits[i]
    return inv


def apply_sbox_int(state_int):
    """
    Aplica a S-Box padrão processando o estado como um único INTEIRO.
    """
    output = 0
    for i in range(32):
        shift = i * 4
        nibble = (state_int >> shift) & 0xF
        subbed = SBOX[nibble]      
        output |= (subbed << shift)
    return output

def linear_layer_int(state_int):
    """
    Permutação padrão (Difusão).
    Converte para bits, permuta e volta para int (Híbrido seguro).
    """
    bits = [(state_int >> (127 - i)) & 1 for i in range(128)]
    
    permuted_bits = [bits[i] for i in P_INDICES]
    
    return bits_to_int(permuted_bits)

def apply_inv_sbox_int(state_int):
    """
    Aplica a S-Box inversa processando o estado como um único INTEIRO.
    Retorna: INTEIRO.
    """
    output = 0
    # Processa 32 nibbles (4 bits) para completar 128 bits
    for i in range(32):
        shift = i * 4
        # Extrai o nibble atual (4 bits)
        nibble = (state_int >> shift) & 0xF
        # Substitui pela S-Box Inversa
        subbed = INV_SBOX[nibble]
        # Coloca o resultado na posição correta
        output |= (subbed << shift)
    return output

def inv_linear_layer_int(state_int):
    """
    Permutação inversa usando índices pré-calculados.
    Recebe INTEIRO, retorna INTEIRO.
    """
    bits = [(state_int >> (127 - i)) & 1 for i in range(128)]
    permuted_bits = [bits[i] for i in INV_P_INDICES] # Usa sua tabela INV_P_INDICES global
    
    return bits_to_int(permuted_bits)

def bits_to_int(bits: List[int]) -> int:
    x = 0
    for b in bits:
        x = (x << 1) | b
    return x
    
def int_to_bits(x: int, size: int) -> List[int]:
    return [(x >> i) & 1 for i in reversed(range(size))]




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

    x = ((time.time_ns() ^ mac) & 0xFFFFFFFF) / (1 << 32)
    for _ in range(8):
        x = 3.99 * x * (1 - x)
    chaos_entropy = int(x * (1 << 32))
    
    combined_int = (mac ^ cursor_entropy ^ os.getpid() ^ chaos_entropy) & 0xFFFFFFFF

    return [(combined_int >> i) & 1 for i in reversed(range(32))]


# ********************************************** Funções principais **********************************************
def GEN(seed_bits: List[int], rounds=16, block_size=128):
    x = bits_to_int(seed_bits[:32]) & 0xFFFFFFFF

    keys = []

    for _ in range(rounds):
        sub = []

        for _ in range(block_size):
            # Xorshift 32
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= (x >> 17)
            x ^= (x << 5) & 0xFFFFFFFF

            sub.append(x & 1)

        keys.append(sub)
    
    return keys



def ENC(keys, M_bits):
    state = bits_to_int(M_bits)

    for i, Ki_bits in enumerate(keys):
        Ki = bits_to_int(Ki_bits)

   
        state ^= Ki

        state = apply_sbox_int(state)

        # Difusão (exceto última rodada)
        if i != len(keys) - 1:
            state = linear_layer_int(state)

    return int_to_bits(state, len(M_bits))



def DEC(keys, C_bits):
    state = bits_to_int(C_bits) 

    if not isinstance(state, int):
        raise TypeError(f"Erro: bits_to_int falhou. state é {type(state)}")
    for i, Ki_bits in enumerate(reversed(keys)):
        
        if i != 0:
            state = inv_linear_layer_int(state)

        state = apply_inv_sbox_int(state)

        Ki = bits_to_int(Ki_bits)
        state ^= Ki

    return int_to_bits(state, len(C_bits))




# ********************************************** TESTES **********************************************

def hamming(A, B):
    return sum(a ^ b for a, b in zip(A, B))


def test_avalanche_message(seed_bits, M, rounds=4):
    keys = GEN(seed_bits, rounds, len(M))
    C1 = ENC(keys, M)

    M2 = M[:]
    M2[0] ^= 1

    C2 = ENC(keys, M2)
    return hamming(C1, C2) / len(M)


def test_avalanche_key(seed_bits, M, rounds=4):
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

def test_collisions(seed_bits, rounds=4, block_size=128, n_tests=10000):
    keys = GEN(seed_bits, rounds, block_size)

    seen = {}
    collisions = 0

    for i in range(n_tests):
        M = [random.randint(0, 1) for _ in range(block_size)]
        C = tuple(ENC(keys, M)) 

        if C in seen:
            if seen[C] != M:
                collisions += 1
        else:
            seen[C] = M

    return collisions



def run_tests(seed_bits, M, rounds=4):
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

    col = test_collisions(seed_bits, rounds, len(M), n_tests=1000)
    print("Colisões encontradas:", col)



# ********************************************** MAIN **********************************************

if __name__ == "__main__":

    s_list = seed()

    MSG_SIZE = 128
    M = [random.randint(0, 1) for _ in range(MSG_SIZE)]

    # Rounds reduzidas para 4 para maior rapidez
    keys = GEN(s_list, rounds=4, block_size=MSG_SIZE)

    C = ENC(keys, M)
    M_dec = DEC(keys, C)

    print("Seed (bits):", s_list)
    print("Mensagem original:", M)
    print("Cifrado:", C)
    print("Decifrado:", M_dec)

    run_tests(s_list, M)