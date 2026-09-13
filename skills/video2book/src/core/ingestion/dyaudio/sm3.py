"""纯 Python 实现的国密 SM3 哈希（GB/T 32905-2016）。

只依赖标准库，因此 a_bogus 签名不需要 ``gmssl`` 等第三方密码库。
"""

from __future__ import annotations

_MASK = 0xFFFFFFFF

_IV = (
    0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
    0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E,
)


def _rotl(x: int, n: int) -> int:
    """32 位循环左移。"""
    n &= 31
    return ((x << n) | (x >> (32 - n))) & _MASK


def _p0(x: int) -> int:
    return x ^ _rotl(x, 9) ^ _rotl(x, 17)


def _p1(x: int) -> int:
    return x ^ _rotl(x, 15) ^ _rotl(x, 23)


def _ff(j: int, x: int, y: int, z: int) -> int:
    if j < 16:
        return x ^ y ^ z
    return (x & y) | (x & z) | (y & z)


def _gg(j: int, x: int, y: int, z: int) -> int:
    if j < 16:
        return x ^ y ^ z
    return (x & y) | ((~x & _MASK) & z)


def _t(j: int) -> int:
    return 0x79CC4519 if j < 16 else 0x7A879D8A


def sm3_hash(data: bytes) -> bytes:
    """返回 32 字节的 SM3 摘要。"""
    msg = bytearray(data)
    bit_len = len(msg) * 8

    # 填充：0x80 → 0x00* → 64bit 大端长度
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0x00)
    msg += bit_len.to_bytes(8, "big")

    v = list(_IV)
    for i in range(0, len(msg), 64):
        block = msg[i:i + 64]
        w = [int.from_bytes(block[j:j + 4], "big") for j in range(0, 64, 4)]
        for j in range(16, 68):
            w.append(
                _p1(w[j - 16] ^ w[j - 9] ^ _rotl(w[j - 3], 15))
                ^ _rotl(w[j - 13], 7)
                ^ w[j - 6]
            )
        w1 = [w[j] ^ w[j + 4] for j in range(64)]

        a, b, c, d, e, f, g, h = v
        for j in range(64):
            a12 = _rotl(a, 12)
            ss1 = _rotl((a12 + e + _rotl(_t(j), j)) & _MASK, 7)
            ss2 = ss1 ^ a12
            tt1 = (_ff(j, a, b, c) + d + ss2 + w1[j]) & _MASK
            tt2 = (_gg(j, e, f, g) + h + ss1 + w[j]) & _MASK

            d = c
            c = _rotl(b, 9)
            b = a
            a = tt1
            h = g
            g = _rotl(f, 19)
            f = e
            e = _p0(tt2)

        v = [x ^ y for x, y in zip(v, (a, b, c, d, e, f, g, h))]

    return b"".join(x.to_bytes(4, "big") for x in v)


def sm3_hex(data: bytes) -> str:
    """返回 64 位小写十六进制字符串。"""
    return sm3_hash(data).hex()


if __name__ == "__main__":  # 自检：SM3("abc") 的标准测试向量
    expected = "66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0"
    got = sm3_hex(b"abc")
    print("SM3('abc') =", got)
    print("self-check :", "PASS" if got == expected else "FAIL")
