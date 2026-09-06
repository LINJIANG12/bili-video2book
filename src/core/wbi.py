"""Bilibili Wbi Signer Implementation.

Handles:
- Dynamic fetching of img_key & sub_key from nav API
- Encoding index permutation to generate mixin_key
- URL query parameters filtering, canonical sorting and MD5 signing (w_rid & wts)
"""

import hashlib
import json
import time
import urllib.parse
import urllib.request
from functools import reduce
from typing import Any, Dict, Optional, Tuple


class WbiSigner:
    NAV_API = "https://api.bilibili.com/x/web-interface/nav"

    # Permutation encoding table from Bilibili Web player
    MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]

    _cached_mixin_key: Optional[str] = None
    _cache_expire_time: float = 0.0

    @classmethod
    def get_mixin_key(cls, orig: str) -> str:
        """Permute raw concatenated keys and take first 32 characters."""
        return reduce(lambda s, i: s + orig[i], cls.MIXIN_KEY_ENC_TAB, "")[:32]

    @classmethod
    def get_wbi_keys(cls, sessdata: Optional[str] = None) -> Tuple[str, str]:
        """Fetch img_key and sub_key from nav endpoint."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.bilibili.com/",
        }
        if sessdata:
            headers["Cookie"] = f"SESSDATA={sessdata}"

        req = urllib.request.Request(cls.NAV_API, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        wbi_img = (data.get("data") or {}).get("wbi_img") or {}
        img_url = wbi_img.get("img_url", "")
        sub_url = wbi_img.get("sub_url", "")

        # Key is the basename without extension
        img_key = img_url.split("/")[-1].split(".")[0]
        sub_key = sub_url.split("/")[-1].split(".")[0]
        return img_key, sub_key

    @classmethod
    def obtain_mixin_key(cls, sessdata: Optional[str] = None) -> str:
        """Obtain mixin_key with memory caching (valid for 1 hour)."""
        now = time.time()
        if cls._cached_mixin_key and now < cls._cache_expire_time:
            return cls._cached_mixin_key

        try:
            img_key, sub_key = cls.get_wbi_keys(sessdata=sessdata)
            mixin_key = cls.get_mixin_key(img_key + sub_key)
            cls._cached_mixin_key = mixin_key
            cls._cache_expire_time = now + 3600  # Cache for 1 hour
            return mixin_key
        except Exception:
            # Fallback default key if nav is blocked temporarily
            fallback_img = "653657f524a14786919221d017849e79"
            fallback_sub = "e2d53442b430485591aa4ebb60d05777"
            return cls.get_mixin_key(fallback_img + fallback_sub)

    @classmethod
    def enc_wbi(cls, params: Dict[str, Any], sessdata: Optional[str] = None) -> Dict[str, Any]:
        """Sign request params by calculating w_rid and appending wts."""
        mixin_key = cls.obtain_mixin_key(sessdata=sessdata)
        curr_params = dict(params)
        curr_params["wts"] = int(time.time())

        # Sort alphabetically by key
        sorted_keys = sorted(curr_params.keys())
        # Filter characters: "!'()*"
        filtered_pairs = []
        for k in sorted_keys:
            val = str(curr_params[k])
            # Characters "!'()*" should be filtered in values
            val_clean = "".join([ch for ch in val if ch not in "!'()*"])
            filtered_pairs.append(f"{urllib.parse.quote_plus(str(k))}={urllib.parse.quote_plus(val_clean)}")

        query_str = "&".join(filtered_pairs)
        w_rid = hashlib.md5((query_str + mixin_key).encode("utf-8")).hexdigest()
        curr_params["w_rid"] = w_rid
        return curr_params
