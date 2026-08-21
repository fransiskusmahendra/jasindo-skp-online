from __future__ import annotations

import hashlib
import hmac
import time
from datetime import date, datetime
from typing import Any

import streamlit as st

PBKDF2_ITERATIONS = 310_000
SESSION_HOURS = 12
MAX_ATTEMPTS = 5
LOCK_SECONDS = 30


def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    ).hex()


def _users() -> dict[str, dict[str, Any]]:
    try:
        raw = st.secrets["users"]
    except Exception:
        return {}
    return {str(k): dict(v) for k, v in dict(raw).items()}


def _find_user(username: str) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    normalized = username.strip().lower()
    for key, record in _users().items():
        configured = str(record.get("username", key)).strip().lower()
        if configured == normalized:
            return key, record
    return None, None


def _parse_expiry(value: Any) -> date | None:
    if value in (None, "", "none", "None"):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _record_is_active(record: dict[str, Any]) -> bool:
    if not bool(record.get("active", True)):
        return False
    expiry = _parse_expiry(record.get("expires_at"))
    return expiry is None or date.today() <= expiry


def _verify_password(password: str, record: dict[str, Any]) -> bool:
    salt = str(record.get("password_salt", ""))
    expected = str(record.get("password_hash", ""))
    if not salt or not expected:
        return False
    try:
        actual = _hash_password(password, salt)
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)


def _clear_auth() -> None:
    for key in ["auth_user_key", "auth_login_at"]:
        st.session_state.pop(key, None)


def _current_user() -> dict[str, Any] | None:
    user_key = st.session_state.get("auth_user_key")
    login_at = st.session_state.get("auth_login_at")
    if not user_key or not login_at:
        return None

    if time.time() - float(login_at) > SESSION_HOURS * 3600:
        _clear_auth()
        return None

    record = _users().get(str(user_key))
    if not record or not _record_is_active(record):
        _clear_auth()
        return None

    return {
        "key": str(user_key),
        "username": str(record.get("username", user_key)),
        "name": str(record.get("name", record.get("username", user_key))),
        "role": str(record.get("role", "user")),
        "expires_at": _parse_expiry(record.get("expires_at")),
    }


def _support_text() -> str:
    try:
        return str(st.secrets.get("app", {}).get("support_contact", "")).strip()
    except Exception:
        return ""


def _render_login() -> None:
    st.markdown(
        """
        <style>
        .login-wrap {max-width: 430px; margin: 8vh auto 0 auto; text-align:center;}
        .login-sub {color:#667085; margin-top:-.25rem; margin-bottom:1.2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="login-wrap"><h2>🔐 SKP Online</h2><div class="login-sub">Akses khusus pelanggan aktif</div></div>', unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.25, 1])
    with center:
        locked_until = float(st.session_state.get("auth_locked_until", 0))
        remaining = int(max(locked_until - time.time(), 0))
        if remaining > 0:
            st.warning(f"Terlalu banyak percobaan login. Coba lagi sekitar {remaining} detik.")
            st.stop()

        with st.form("customer_login", clear_on_submit=False):
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Masuk", type="primary", use_container_width=True)

        if submitted:
            key, record = _find_user(username)
            valid = bool(record) and _record_is_active(record) and _verify_password(password, record)
            if valid and key is not None:
                st.session_state["auth_user_key"] = key
                st.session_state["auth_login_at"] = time.time()
                st.session_state["auth_attempts"] = 0
                st.session_state.pop("auth_locked_until", None)
                st.rerun()

            attempts = int(st.session_state.get("auth_attempts", 0)) + 1
            st.session_state["auth_attempts"] = attempts
            if attempts >= MAX_ATTEMPTS:
                st.session_state["auth_attempts"] = 0
                st.session_state["auth_locked_until"] = time.time() + LOCK_SECONDS
            st.error("Username/password salah, akun tidak aktif, atau masa akses sudah berakhir.")

        support = _support_text()
        if support:
            st.caption(f"Butuh akses atau perpanjangan? Hubungi {support}")
        else:
            st.caption("Akun diberikan setelah aktivasi layanan.")


def require_login() -> dict[str, Any]:
    user = _current_user()
    if user is not None:
        return user

    if not _users():
        st.error("Akses belum dikonfigurasi. Administrator perlu menambahkan akun pelanggan di Streamlit Secrets.")
        st.stop()

    _render_login()
    st.stop()


def render_account_sidebar(user: dict[str, Any]) -> None:
    with st.sidebar:
        st.caption(f"Masuk sebagai **{user['name']}**")
        expiry = user.get("expires_at")
        if expiry:
            st.caption(f"Akses aktif s.d. **{expiry.strftime('%d-%m-%Y')}**")
        if st.button("Keluar", use_container_width=True, key="logout_button"):
            _clear_auth()
            st.rerun()
