"""Map provider listing and custom provider management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..deps import AdminDep, SessionDep
from ..schemas import CustomProviderCreate, ProviderKeyUpdate, ProviderOut
from ..services import providers as prov_svc
from ..settings_store import CUSTOM_PROVIDERS_KEY, get_setting, set_setting

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderOut])
def list_providers(session: SessionDep):
    return prov_svc.list_providers(session)


@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider(provider_id: str, session: SessionDep):
    provider = prov_svc.get_provider(provider_id, session)
    if provider is None:
        raise HTTPException(status_code=404, detail="Unknown provider")
    d = provider.to_dict()
    d["has_key"] = d["has_key"] or bool(
        get_setting(session, f"provider_key:{provider_id}")
    )
    return d


@router.post("/{provider_id}/key", status_code=204)
def set_provider_key(provider_id: str, payload: ProviderKeyUpdate, session: SessionDep, admin: AdminDep):
    set_setting(session, f"provider_key:{provider_id}", payload.key)
    return None


@router.delete("/{provider_id}/key", status_code=204)
def clear_provider_key(provider_id: str, session: SessionDep, admin: AdminDep):
    from ..settings_store import delete_setting

    delete_setting(session, f"provider_key:{provider_id}")
    return None


@router.post("/custom", response_model=ProviderOut, status_code=201)
def create_custom_provider(payload: CustomProviderCreate, session: SessionDep, admin: AdminDep):
    existing = prov_svc.load_providers(session)
    slug = prov_svc._slug(payload.name)
    if slug in existing:
        raise HTTPException(status_code=409, detail=f"Provider '{payload.name}' already exists")
    custom = get_setting(session, CUSTOM_PROVIDERS_KEY, [])
    entry = {
        "id": slug,
        "name": payload.name,
        "url_template": payload.url_template,
        "subdomains": payload.subdomains,
        "attribution": payload.attribution,
        "license": payload.license,
        "kind": payload.kind,
        "format": payload.format,
        "min_zoom": payload.min_zoom,
        "max_zoom": payload.max_zoom,
        "estimated_bytes_per_tile": payload.estimated_bytes_per_tile,
        "description": "Custom provider added by administrator",
        "offline_allowed": True,
    }
    custom.append(entry)
    set_setting(session, CUSTOM_PROVIDERS_KEY, custom)
    return prov_svc.Provider(**entry).to_dict()


@router.delete("/custom/{provider_id}", status_code=204)
def delete_custom_provider(provider_id: str, session: SessionDep, admin: AdminDep):
    custom = get_setting(session, CUSTOM_PROVIDERS_KEY, [])
    remaining = [c for c in custom if c.get("id") != provider_id]
    if len(remaining) == len(custom):
        raise HTTPException(status_code=404, detail="Custom provider not found")
    set_setting(session, CUSTOM_PROVIDERS_KEY, remaining)
    return None
