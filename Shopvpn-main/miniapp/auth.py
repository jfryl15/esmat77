# -*- coding: utf-8 -*-
"""
اعتبارسنجی initData مینی‌اپ تلگرام.
الگوریتم رسمی: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
هرگز به user_id ارسالی از کلاینت اعتماد نکن؛ همیشه از همین تابع عبور بده.
"""

import hashlib
import hmac
import logging
from urllib.parse import parse_qsl

logger = logging.getLogger("miniapp.auth")


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400):
    """اگر معتبر باشد، دیکشنری پارس‌شده (شامل user) را برمی‌گرداند؛ وگرنه None."""
    if not init_data:
        logger.warning("initData خالی است.")
        return None

    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as e:
        logger.warning("initData قابل پارس نیست: %s | raw=%r", e, init_data[:200])
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        logger.warning("initData بدون فیلد hash است. keys=%s", list(pairs.keys()))
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        logger.warning(
            "عدم تطابق هش initData. token_used=...%s computed=%s received=%s data_check_string=%r",
            bot_token[-6:], computed_hash, received_hash, data_check_string,
        )
        return None

    auth_date = pairs.get("auth_date")
    if not auth_date:
        logger.warning("initData بدون فیلد auth_date است.")
        return None

    try:
        import time
        auth_timestamp = int(auth_date)
    except (TypeError, ValueError):
        logger.warning("auth_date در initData معتبر نیست: %r", auth_date)
        return None

    # درخواست های آینده نگر یا خیلی قدیمی نباید پذیرفته شوند. تلگرام همیشه
    # timestamp ثانیه ای فعلی می فرستد؛ یک تلورانس کوچک برای اختلاف ساعت کافی است.
    now = time.time()
    if auth_timestamp > now + 60 or now - auth_timestamp > max_age_seconds:
        logger.warning("auth_date در initData خارج از بازه ی مجاز است.")
        return None

    if "user" not in pairs:
        logger.warning("initData بدون فیلد user است.")
        return None
    try:
        import json
        user = json.loads(pairs["user"])
    except (TypeError, ValueError, json.JSONDecodeError):
        logger.warning("فیلد user در initData قابل پارس نیست.")
        return None
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        logger.warning("فیلد user در initData معتبر نیست.")
        return None
    pairs["user"] = user
    return pairs
