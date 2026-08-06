"""External authentication backends: OpenID Connect and LDAP.

OIDC is implemented with httpx + PyJWT (JWKS verification); LDAP uses the
optional ``ldap3`` package. Both are configured by administrators via the
settings API and are entirely optional.
"""

from __future__ import annotations

import asyncio
import secrets
import time
import urllib.parse
from typing import Any

import httpx

from .logging import log

JWK_CACHE_TTL = 300


# --- OpenID Connect -----------------------------------------------------------

class OidcManager:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}
        self._jwks_cache: dict[str, tuple[float, list[dict]]] = {}

    def providers(self, providers_config: list[dict]) -> list[dict]:
        return [
            {"id": p.get("id"), "name": p.get("name") or p.get("id"), "login_url": f"/api/auth/oidc/login/{p.get('id')}"}
            for p in providers_config
        ]

    def new_state(self, provider_id: str) -> str:
        state = secrets.token_urlsafe(24)
        self._states[state] = {"provider": provider_id, "ts": time.time()}
        self._cleanup_states()
        return state

    def _cleanup_states(self) -> None:
        now = time.time()
        for s in list(self._states):
            if now - self._states[s]["ts"] > 900:
                del self._states[s]

    async def build_login_url(self, providers_config: list[dict], provider_id: str,
                              base_url: str) -> str:
        provider = next((p for p in providers_config if p.get("id") == provider_id), None)
        if not provider:
            raise KeyError(provider_id)
        discovery = await self._discover(provider["issuer"])
        state = self.new_state(provider_id)
        params = {
            "response_type": "code",
            "client_id": provider["client_id"],
            "redirect_uri": f"{base_url}/api/auth/oidc/callback",
            "scope": provider.get("scope") or "openid profile email",
            "state": state,
            "nonce": secrets.token_urlsafe(16),
        }
        self._states[state]["nonce"] = params["nonce"]
        return f"{discovery['authorization_endpoint']}?{urllib.parse.urlencode(params)}"

    async def exchange(self, providers_config: list[dict], code: str, state: str,
                       base_url: str) -> dict[str, Any]:
        entry = self._states.pop(state, None)
        if not entry:
            raise ValueError("Invalid or expired OIDC state")
        provider = next((p for p in providers_config if p.get("id") == entry["provider"]), None)
        if not provider:
            raise ValueError("Unknown OIDC provider")
        discovery = await self._discover(provider["issuer"])

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(discovery["token_endpoint"], data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{base_url}/api/auth/oidc/callback",
                "client_id": provider["client_id"],
                "client_secret": provider.get("client_secret", ""),
            })
            resp.raise_for_status()
            token = resp.json()
        id_token = token.get("id_token")
        if not id_token:
            raise ValueError("No id_token returned by provider")

        claims = await self._verify_id_token(provider, id_token, entry.get("nonce"))
        sub = str(claims.get("sub") or "")
        if not sub:
            raise ValueError("No subject in id_token")

        return {
            "sub": sub,
            "provider_id": provider["id"],
            "username": claims.get("preferred_username") or claims.get("name") or claims.get("email") or f"oidc-{sub[:8]}",
            "email": claims.get("email") or "",
        }

    async def _verify_id_token(self, provider: dict, token: str, nonce: str | None) -> dict:
        import jwt as pyjwt

        keys = await _fetch_jwks(provider["issuer"])
        self._jwks_cache[provider["issuer"]] = (time.time(), keys)
        unverified = pyjwt.decode(token, options={"verify_signature": False})
        kid = unverified.get("kid")
        jwk = None
        if kid:
            jwk = next((k for k in keys if k.get("kid") == kid), None)
        if jwk is None and keys:
            jwk = keys[0]
        if jwk is None:
            raise ValueError("No usable JWK for provider")
        public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(jwk) if jwk.get("kty") == "RSA" \
            else pyjwt.algorithms.ECAlgorithm.from_jwk(jwk)
        claims = pyjwt.decode(token, public_key, algorithms=[jwk.get("alg") or "RS256"],
                              audience=provider["client_id"])
        if nonce and claims.get("nonce") != nonce:
            raise ValueError("nonce mismatch")
        return claims

    def _jwks(self, issuer: str) -> list[dict]:
        now = time.time()
        cached = self._jwks_cache.get(issuer)
        if cached and now - cached[0] < JWK_CACHE_TTL:
            return cached[1]
        keys = asyncio.run(_fetch_jwks(issuer))  # called from sync context; rare
        self._jwks_cache[issuer] = (now, keys)
        return keys

    async def _discover(self, issuer: str) -> dict:
        url = issuer.rstrip("/") + "/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()


async def _fetch_jwks(issuer: str) -> list[dict]:
    from .providers import Provider  # noqa

    async with httpx.AsyncClient(timeout=20.0) as client:
        disco = await client.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
        disco.raise_for_status()
        jwks_url = disco.json().get("jwks_uri")
        if not jwks_url:
            return []
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        return resp.json().get("keys", [])


# --- LDAP --------------------------------------------------------------------

def ldap_authenticate(config: dict, username: str, password: str) -> dict[str, str] | None:
    """Attempt an LDAP bind. Returns attribute mapping on success or None."""
    if not password:
        return None
    try:
        import ldap3
    except ImportError:
        log.warning("ldap3 not installed — LDAP auth unavailable (pip install maparr[ldap])")
        return None
    server = ldap3.Server(config.get("url", "ldap://localhost:389"), get_info=ldap3.NONE)
    bind_dn = config.get("bind_dn") or ""
    bind_pw = config.get("bind_password") or ""
    conn = ldap3.Connection(server, user=bind_dn, password=bind_pw, auto_bind=True)
    user_filter = config.get("user_filter") or "(uid={username})"
    search_filter = user_filter.replace("{username}", ldap3.utils.conv.escape_filter_chars(username))
    conn.search(
        search_base=config.get("user_base_dn", ""),
        search_filter=search_filter,
        attributes=[v for v in (config.get("user_attr_map") or {}).values()],
    )
    if not conn.entries:
        return None
    entry = conn.entries[0]
    attr_map = config.get("user_attr_map") or {}
    out = {"username": username}
    if "email" in attr_map:
        email = getattr(entry, attr_map["email"], None)
        if email is not None:
            out["email"] = str(email)
    # Verify password via user bind.
    user_dn = entry.entry_dn
    conn2 = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True)
    if not conn2.bound:
        return None
    return out


def ldap_default_role(config: dict) -> str:
    return config.get("default_role") or "user"


_oidc: OidcManager | None = None


def get_oidc() -> OidcManager:
    global _oidc
    if _oidc is None:
        _oidc = OidcManager()
    return _oidc
