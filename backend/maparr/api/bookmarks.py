"""User bookmarks and favorites."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from ..deps import SessionDep, UserDep
from ..models import Bookmark, User
from ..schemas import BookmarkCreate, BookmarkOut, BookmarkUpdate

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


def _owns(bookmark: Bookmark, user: User) -> bool:
    return bookmark.user_id == user.id or user.role == "admin"


@router.get("", response_model=list[BookmarkOut])
def list_bookmarks(session: SessionDep, user: UserDep,
                   favorites_only: bool = False):
    q = session.query(Bookmark).filter(Bookmark.user_id == user.id)
    if favorites_only:
        q = q.filter(Bookmark.is_favorite.is_(True))
    return q.order_by(Bookmark.created_at.desc()).all()


@router.post("", response_model=BookmarkOut, status_code=201)
def create_bookmark(payload: BookmarkCreate, session: SessionDep, user: UserDep):
    book = Bookmark(**payload.model_dump(), user_id=user.id,
                    share_token=secrets.token_urlsafe(16))
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


@router.get("/{bookmark_id}", response_model=BookmarkOut)
def get_bookmark(bookmark_id: str, session: SessionDep, user: UserDep):
    book = session.get(Bookmark, bookmark_id)
    if book is None or not _share(book, user):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return book


@router.patch("/{bookmark_id}", response_model=BookmarkOut)
def update_bookmark(bookmark_id: str, payload: BookmarkUpdate,
                    session: SessionDep, user: UserDep):
    book = session.get(Bookmark, bookmark_id)
    if book is None or not _share(book, user):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    session.commit()
    session.refresh(book)
    return book


@router.delete("/{bookmark_id}", status_code=204)
def delete_bookmark(bookmark_id: str, session: SessionDep, user: UserDep):
    book = session.get(Bookmark, bookmark_id)
    if book is None or not _share(book, user):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    session.delete(book)
    session.commit()
    return None


@router.get("/share/{token}")
def open_share(token: str, session: SessionDep, user: UserDep):
    book = session.query(Bookmark).filter(Bookmark.share_token == token).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Shared location not found")
    return {
        "name": book.name,
        "lat": book.lat,
        "lon": book.lon,
        "zoom": book.zoom,
        "shared_by": book.user.username if book.user else "",
    }