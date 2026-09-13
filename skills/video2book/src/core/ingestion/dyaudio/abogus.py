"""抖音 Web 端 ``a_bogus`` 请求签名 —— 纯 Python 实现。

背景
----
抖音 Web 接口（``/aweme/v1/web/...``）会校验查询串上的 ``a_bogus`` 参数；
缺失或错误时返回 ``{"status_code": 8/10111, "status_msg": "invalid a_bogus"}``。
本模块把该算法从混淆 JS 移植为纯 Python：**不依赖 Node.js、不启动浏览器**，
仅使用标准库 + 本包的 :mod:`dyaudio.sm3`。

算法链路
--------
1. ``params`` 与 ``body`` 各自做「加盐 SM3 两次」（盐为 ``cus``，第二次输入是第一次的
   32 个原始字节而非 hex 文本）；
2. UA 经 RC4（key=``\\x00\\x01\\x0e``）+ 自定义 Base64 + SM3；
3. 时间戳 / 请求方法 / aid / pageId / 浏览器指纹等写入 ``ab_dir``；
4. 按 ``sort_index`` 取值、按 ``sort_index_2`` 逐项异或，再做字节变换；
5. 自定义 Base64 编码，前置 12 字节随机混淆串 → 最终 ``a_bogus``。

实现参考
--------
算法结构与常量参考开源项目 ``f2``（作者 JohnserfSeed，Apache-2.0，
https://github.com/Johnserf-Seed/f2 ）中的 ``utils/abogus.py``；
SM3 由本包 :mod:`dyaudio.sm3` 提供，去掉了 ``gmssl`` 依赖。

免责声明
--------
本实现仅用于技术学习与研究。请遵守目标平台的服务条款与所在地区法律法规，
不要用于任何未授权的数据抓取或商业用途。
"""

from __future__ import annotations

import random
import time
from typing import Dict, List, Union

from .sm3 import sm3_hash


class _StringProcessor:
    """字符串 / ASCII 互转与伪随机字节生成。"""

    @staticmethod
    def to_char_str(codes: List[int]) -> str:
        return "".join(chr(c) for c in codes)

    @staticmethod
    def to_char_array(text: str) -> List[int]:
        return [ord(c) for c in text]

    @staticmethod
    def js_shift_right(val: int, n: int) -> int:
        """模拟 JS 的 ``>>>`` 无符号右移。"""
        return (val % 0x100000000) >> n

    @staticmethod
    def generate_random_bytes(length: int = 3) -> str:
        """生成 4*length 字节伪随机串，用于前置混淆。"""

        def _seq() -> List[str]:
            rd = int(random.random() * 10000)
            return [
                chr(((rd & 255) & 170) | 1),
                chr(((rd & 255) & 85) | 2),
                chr((_StringProcessor.js_shift_right(rd, 8) & 170) | 5),
                chr((_StringProcessor.js_shift_right(rd, 8) & 85) | 40),
            ]

        out: List[str] = []
        for _ in range(length):
            out.extend(_seq())
        return "".join(out)


# 字节变换所用的固定置换表（256 项）
_BIG_ARRAY = [
    121, 243, 55, 234, 103, 36, 47, 228, 30, 231, 106, 6, 115, 95,
    78, 101, 250, 207, 198, 50, 139, 227, 220, 105, 97, 143, 34, 28,
    194, 215, 18, 100, 159, 160, 43, 8, 169, 217, 180, 120, 247, 45,
    90, 11, 27, 197, 46, 3, 84, 72, 5, 68, 62, 56, 221, 75, 144, 79,
    73, 161, 178, 81, 64, 187, 134, 117, 186, 118, 16, 241, 130, 71,
    89, 147, 122, 129, 65, 40, 88, 150, 110, 219, 199, 255, 181, 254,
    48, 4, 195, 248, 208, 32, 116, 167, 69, 201, 17, 124, 125, 104,
    96, 83, 80, 127, 236, 108, 154, 126, 204, 15, 20, 135, 112, 158,
    13, 1, 188, 164, 210, 237, 222, 98, 212, 77, 253, 42, 170, 202,
    26, 22, 29, 182, 251, 10, 173, 152, 58, 138, 54, 141, 185, 33,
    157, 31, 252, 132, 233, 235, 102, 196, 191, 223, 240, 148, 39, 123,
    92, 82, 128, 109, 57, 24, 38, 113, 209, 245, 2, 119, 153, 229,
    189, 214, 230, 174, 232, 63, 52, 205, 86, 140, 66, 175, 111, 171,
    246, 133, 238, 193, 99, 60, 74, 91, 225, 51, 76, 37, 145, 211,
    166, 151, 213, 206, 0, 200, 244, 176, 218, 44, 184, 172, 49, 216,
    93, 168, 53, 21, 183, 41, 67, 85, 224, 155, 226, 242, 87, 177,
    146, 70, 190, 12, 162, 19, 137, 114, 25, 165, 163, 192, 23, 59,
    9, 94, 179, 107, 35, 7, 142, 131, 239, 203, 149, 136, 61, 249, 14, 156,
]


class _CryptoUtility:
    """SM3、盐值、字节变换、自定义 Base64、RC4。"""

    def __init__(self, salt: str, alphabets: List[str]):
        self.salt = salt
        self.base64_alphabet = alphabets

    @staticmethod
    def sm3_to_array(data: Union[str, List[int], bytes]) -> List[int]:
        if isinstance(data, str):
            raw = data.encode("utf-8")
        elif isinstance(data, bytes):
            raw = data
        else:
            raw = bytes(data)
        return list(sm3_hash(raw))

    def add_salt(self, param: str) -> str:
        return param + self.salt

    def params_to_array(self, param: Union[str, List[int]], add_salt: bool = True) -> List[int]:
        if isinstance(param, str) and add_salt:
            param = self.add_salt(param)
        return self.sm3_to_array(param)

    def transform_bytes(self, bytes_list: List[int]) -> str:
        """对字节列表做一次可逆的置换-异或变换（字节变换核心）。"""
        big = list(_BIG_ARRAY)  # 每次调用使用全新表，保证结果可复现
        bytes_str = _StringProcessor.to_char_str(bytes_list)
        result: List[str] = []

        index_b = big[1]
        initial_value = 0
        value_e = 0
        for index, ch in enumerate(bytes_str):
            if index == 0:
                initial_value = big[index_b]
                sum_initial = index_b + initial_value
                big[1] = initial_value
                big[index_b] = index_b
            else:
                sum_initial = initial_value + value_e

            sum_initial %= len(big)
            value_f = big[sum_initial]
            result.append(chr(ord(ch) ^ value_f))

            value_e = big[(index + 2) % len(big)]
            sum_initial = (index_b + value_e) % len(big)
            initial_value = big[sum_initial]
            big[sum_initial] = big[(index + 2) % len(big)]
            big[(index + 2) % len(big)] = initial_value
            index_b = sum_initial

        return "".join(result)

    def base64_encode(self, text: str, alphabet_index: int = 0) -> str:
        """自定义字符表的 Base64 编码（用于 UA 摘要）。"""
        binary = "".join(f"{ord(c):08b}" for c in text)
        padding = (6 - len(binary) % 6) % 6
        binary += "0" * padding
        indices = [int(binary[i:i + 6], 2) for i in range(0, len(binary), 6)]
        out = "".join(self.base64_alphabet[alphabet_index][i] for i in indices)
        out += "=" * (padding // 2)
        return out

    def abogus_encode(self, raw: str, alphabet_index: int) -> str:
        """最终 a_bogus 的自定义 Base64 编码。"""
        out: List[str] = []
        alphabet = self.base64_alphabet[alphabet_index]
        for i in range(0, len(raw), 3):
            if i + 2 < len(raw):
                n = (ord(raw[i]) << 16) | (ord(raw[i + 1]) << 8) | ord(raw[i + 2])
            elif i + 1 < len(raw):
                n = (ord(raw[i]) << 16) | (ord(raw[i + 1]) << 8)
            else:
                n = ord(raw[i]) << 16

            for j, k in zip(range(18, -1, -6), (0xFC0000, 0x03F000, 0x0FC0, 0x3F)):
                if j == 6 and i + 1 >= len(raw):
                    break
                if j == 0 and i + 2 >= len(raw):
                    break
                out.append(alphabet[(n & k) >> j])

        out.append("=" * ((4 - len(out) % 4) % 4))
        return "".join(out)

    @staticmethod
    def rc4_encrypt(key: bytes, plaintext: str) -> bytes:
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + key[i % len(key)]) % 256
            s[i], s[j] = s[j], s[i]
        i = j = 0
        cipher: List[int] = []
        for ch in plaintext:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            cipher.append(ord(ch) ^ s[(s[i] + s[j]) % 256])
        return bytes(cipher)


class BrowserFingerprintGenerator:
    """生成形如 ``w|h|ow|oh|...|Win32`` 的浏览器指纹串。"""

    @classmethod
    def generate_fingerprint(cls, browser_type: str = "Edge") -> str:
        platform = "MacIntel" if browser_type == "Safari" else "Win32"
        return cls._generate_fingerprint(platform)

    @staticmethod
    def _generate_fingerprint(platform: str) -> str:
        inner_width = random.randint(1024, 1920)
        inner_height = random.randint(768, 1080)
        outer_width = inner_width + random.randint(24, 32)
        outer_height = inner_height + random.randint(75, 90)
        screen_x = 0
        screen_y = random.choice([0, 30])
        size_width = random.randint(1024, 1920)
        size_height = random.randint(768, 1080)
        avail_width = random.randint(1280, 1920)
        avail_height = random.randint(800, 1080)
        return (
            f"{inner_width}|{inner_height}|{outer_width}|{outer_height}|"
            f"{screen_x}|{screen_y}|0|0|{size_width}|{size_height}|"
            f"{avail_width}|{avail_height}|{inner_width}|{inner_height}|24|24|{platform}"
        )


_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
)


class ABogus:
    """a_bogus 签名器。

    用法::

        signer = ABogus(user_agent=ua)
        a_bogus = signer.sign("device_platform=webapp&aid=6383&...")

    ``sign`` 返回的字符串需以 URL 编码形式追加为查询参数 ``a_bogus``。
    """

    AID = 6383
    PAGE_ID = 0
    SALT = "cus"
    UA_KEY = b"\x00\x01\x0e"

    _CHARACTER = "Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe"
    _CHARACTER2 = "ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe"

    _SORT_INDEX = [
        18, 20, 52, 26, 30, 34, 58, 38, 40, 53, 42, 21, 27, 54, 55, 31, 35, 57,
        39, 41, 43, 22, 28, 32, 60, 36, 23, 29, 33, 37, 44, 45, 59, 46, 47, 48,
        49, 50, 24, 25, 65, 66, 70, 71,
    ]
    _SORT_INDEX_2 = [
        18, 20, 26, 30, 34, 38, 40, 42, 21, 27, 31, 35, 39, 41, 43, 22, 28, 32,
        36, 23, 29, 33, 37, 44, 45, 46, 47, 48, 49, 50, 24, 25, 52, 53, 54, 55,
        57, 58, 59, 60, 65, 66, 70, 71,
    ]

    def __init__(self, user_agent: str = "", fp: str = "", options: List[int] = None):
        self.aid = self.AID
        self.page_id = self.PAGE_ID
        self.boe = False
        self.ddrt = 8.5
        self.paths = [
            "^/webcast/", "^/aweme/v1/", "^/aweme/v2/",
            "/v1/message/send", "^/live/", "^/captcha/", "^/ecom/",
        ]
        self.options = options or [0, 1, 14]  # GET [0,1,8] / POST [0,1,14]
        self.user_agent = user_agent or _DEFAULT_UA
        self.browser_fp = fp or BrowserFingerprintGenerator.generate_fingerprint("Edge")
        self.crypto = _CryptoUtility(self.SALT, [self._CHARACTER, self._CHARACTER2])

    # ------------------------------------------------------------------ #
    # 内部步骤
    # ------------------------------------------------------------------ #
    def _ua_digest(self) -> List[int]:
        rc4 = self.crypto.rc4_encrypt(self.UA_KEY, self.user_agent)
        b64 = self.crypto.base64_encode(_StringProcessor.to_char_str(list(rc4)), 1)
        return self.crypto.sm3_to_array(b64)

    def _build_ab_dir(self, params: str, body: str) -> Dict[int, int]:
        ab_dir: Dict[int, int] = {
            8: 3,
            15: {
                "aid": self.aid,
                "pageId": self.page_id,
                "boe": self.boe,
                "ddrt": self.ddrt,
                "paths": self.paths,
                "track": {"mode": 0, "delay": 300, "paths": []},
                "dump": True,
                "rpU": "",
            },
            18: 44,
            19: [1, 0, 1, 0, 1],
            66: 0,
            69: 0,
            70: 0,
            71: 0,
        }

        start = int(time.time() * 1000)
        array1 = self.crypto.params_to_array(self.crypto.params_to_array(params))
        array2 = self.crypto.params_to_array(self.crypto.params_to_array(body))
        array3 = self._ua_digest()
        end = int(time.time() * 1000)

        ab_dir[20] = (start >> 24) & 255
        ab_dir[21] = (start >> 16) & 255
        ab_dir[22] = (start >> 8) & 255
        ab_dir[23] = start & 255
        ab_dir[24] = int(start / 256 / 256 / 256 / 256)
        ab_dir[25] = int(start / 256 / 256 / 256 / 256 / 256)

        ab_dir[26] = (self.options[0] >> 24) & 255
        ab_dir[27] = (self.options[0] >> 16) & 255
        ab_dir[28] = (self.options[0] >> 8) & 255
        ab_dir[29] = self.options[0] & 255

        ab_dir[30] = int(self.options[1] / 256) & 255
        ab_dir[31] = (self.options[1] % 256) & 255
        ab_dir[32] = (self.options[1] >> 24) & 255
        ab_dir[33] = (self.options[1] >> 16) & 255

        ab_dir[34] = (self.options[2] >> 24) & 255
        ab_dir[35] = (self.options[2] >> 16) & 255
        ab_dir[36] = (self.options[2] >> 8) & 255
        ab_dir[37] = self.options[2] & 255

        ab_dir[38] = array1[21]
        ab_dir[39] = array1[22]
        ab_dir[40] = array2[21]
        ab_dir[41] = array2[22]
        ab_dir[42] = array3[23]
        ab_dir[43] = array3[24]

        ab_dir[44] = (end >> 24) & 255
        ab_dir[45] = (end >> 16) & 255
        ab_dir[46] = (end >> 8) & 255
        ab_dir[47] = end & 255
        ab_dir[48] = ab_dir[8]
        ab_dir[49] = int(end / 256 / 256 / 256 / 256)
        ab_dir[50] = int(end / 256 / 256 / 256 / 256 / 256)

        ab_dir[51] = (self.page_id >> 24) & 255
        ab_dir[52] = (self.page_id >> 16) & 255
        ab_dir[53] = (self.page_id >> 8) & 255
        ab_dir[54] = self.page_id & 255
        ab_dir[55] = self.page_id
        ab_dir[56] = self.aid
        ab_dir[57] = self.aid & 255
        ab_dir[58] = (self.aid >> 8) & 255
        ab_dir[59] = (self.aid >> 16) & 255
        ab_dir[60] = (self.aid >> 24) & 255

        fp_len = len(self.browser_fp)
        ab_dir[64] = fp_len
        ab_dir[65] = fp_len
        return ab_dir

    # ------------------------------------------------------------------ #
    # 对外接口
    # ------------------------------------------------------------------ #
    def sign(self, params: str, body: str = "") -> str:
        """根据查询串（已 URL 编码）生成 ``a_bogus``。"""
        ab_dir = self._build_ab_dir(params, body)

        sorted_values = [ab_dir.get(i, 0) for i in self._SORT_INDEX]

        # 浏览器指纹逐字符 + 异或校验位
        fp_codes = _StringProcessor.to_char_array(self.browser_fp)
        ab_xor = (len(self.browser_fp) & 255) >> 8 & 255
        for index in range(len(self._SORT_INDEX_2) - 1):
            if index == 0:
                ab_xor = ab_dir.get(self._SORT_INDEX_2[index], 0)
            ab_xor ^= ab_dir.get(self._SORT_INDEX_2[index + 1], 0)

        sorted_values.extend(fp_codes)
        sorted_values.append(ab_xor)

        raw = (
            _StringProcessor.generate_random_bytes()
            + self.crypto.transform_bytes(sorted_values)
        )
        return self.crypto.abogus_encode(raw, 0)


if __name__ == "__main__":
    from urllib.parse import urlencode

    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    )
    signer = ABogus(user_agent=ua, fp=BrowserFingerprintGenerator.generate_fingerprint("Edge"))
    params = urlencode({
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "sec_user_id": "MS4wLjABAAAAexample",
        "max_cursor": "0",
        "count": "18",
    })
    print("a_bogus =", signer.sign(params))
