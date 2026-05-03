import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, computed_field


class ChannelConnectionCreate(BaseModel):
    channel_type: str
    account_name: str | None = None
    account_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    extra_data: dict[str, Any] | None = None


class ChannelAccountSelection(BaseModel):
    selected_id: str


class ChannelConnectionResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    channel_type: str
    account_name: str | None
    account_id: str | None
    is_connected: bool
    connected_at: datetime | None
    token_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Token-bearing provider metadata is needed only to derive public display
    # fields below. It must never be serialized to API clients.
    extra_data: dict[str, Any] | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def facebook_page_id(self) -> str | None:
        if self.channel_type != "facebook":
            return None
        if self.account_id:
            return self.account_id
        pages = (self.extra_data or {}).get("pages")
        if isinstance(pages, list) and pages:
            page_id = pages[0].get("id") if isinstance(pages[0], dict) else None
            return str(page_id) if page_id else None
        return None

    @computed_field
    @property
    def facebook_page_name(self) -> str | None:
        if self.channel_type != "facebook":
            return None
        pages = (self.extra_data or {}).get("pages")
        if isinstance(pages, list) and pages:
            page_name = pages[0].get("name") if isinstance(pages[0], dict) else None
            return str(page_name) if page_name else None
        return None

    @computed_field
    @property
    def facebook_page_count(self) -> int | None:
        if self.channel_type != "facebook":
            return None
        pages = (self.extra_data or {}).get("pages")
        return len(pages) if isinstance(pages, list) else 0

    @computed_field
    @property
    def channel_choices(self) -> list[dict[str, Any]]:
        raw_choices = (self.extra_data or {}).get("channel_choices")
        if not isinstance(raw_choices, list):
            return []
        safe_choices: list[dict[str, Any]] = []
        for choice in raw_choices:
            if not isinstance(choice, dict) or not choice.get("id"):
                continue
            safe_choices.append({
                key: value
                for key, value in choice.items()
                if key not in {"access_token", "page_access_token", "token", "secret"}
            })
        return safe_choices

    @computed_field
    @property
    def selection_required(self) -> bool:
        return not bool(self.account_id) and bool(self.channel_choices)

    @computed_field
    @property
    def display_account_id(self) -> str | None:
        if self.channel_type == "facebook":
            profile = (self.extra_data or {}).get("facebook_profile")
            if isinstance(profile, dict) and profile.get("id"):
                return str(profile["id"])
        if self.channel_type in {"instagram", "threads"}:
            profile = (self.extra_data or {}).get("meta_profile")
            if isinstance(profile, dict) and profile.get("id"):
                return str(profile["id"])
        return self.account_id

    @computed_field
    @property
    def display_account_name(self) -> str | None:
        if self.channel_type == "facebook":
            profile = (self.extra_data or {}).get("facebook_profile")
            if isinstance(profile, dict) and profile.get("name"):
                return str(profile["name"])
        if self.channel_type in {"instagram", "threads"}:
            profile = (self.extra_data or {}).get("meta_profile")
            if isinstance(profile, dict):
                name = profile.get("username") or profile.get("name")
                if name:
                    return str(name)
        return self.account_name

    model_config = {"from_attributes": True}
