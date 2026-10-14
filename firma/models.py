import re
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

Status = Literal["research", "qualified", "contacted", "replied", "not_suitable"]
Fit = Literal["unknown", "possible", "confirmed", "no"]
COUNTRIES = {"FR": "France", "TR": "Türkiye", "DE": "Germany", "GB": "United Kingdom", "US": "United States", "IT": "Italy", "ES": "Spain", "NL": "Netherlands", "BE": "Belgium", "CH": "Switzerland", "ALL": ""}


def public_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        p = urlsplit(value)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.port not in (None, 80, 443):
            raise ValueError()
        if any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
            raise ValueError()
    except ValueError:
        raise ValueError("Geçerli bir http/https adresi girin.")
    return urlunsplit((p.scheme, p.netloc.lower(), p.path or "/", p.query, ""))


def domain_key(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    if host in ("instagram.com", "facebook.com", "etsy.com"):
        return host + "/" + urlsplit(url).path.strip("/").split("/")[0].lower()
    return host


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    mode: Literal["product", "city", "general", "prospects"] = "product"
    product: str = Field(default="", max_length=160)
    city: str = Field(default="", max_length=100)
    query: str = Field(default="", max_length=250)
    country: str = "FR"
    language: Literal["fr", "tr", "en", "de", "it", "es", "nl"] = "fr"
    sector: Literal["all", "fashion", "home", "baby", "accessories"] = "all"
    page: int = Field(default=1, ge=1, le=5)

    @model_validator(mode="after")
    def validate_query(self):
        if self.country not in COUNTRIES:
            raise ValueError("Desteklenmeyen ülke.")
        needed = {"product": self.product, "city": self.city, "general": self.query}
        if self.mode != "prospects" and len(needed[self.mode]) < 2:
            raise ValueError("Arama alanına en az 2 karakter yazın.")
        if self.mode == "prospects" and (self.product or self.query):
            raise ValueError("Potansiyel keşfi anahtar kelime kullanmaz.")
        if self.mode == "prospects" and self.country == "ALL" and not self.city:
            raise ValueError("Potansiyel keşfi için ülke veya şehir seçin.")
        return self


class Lead(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=200)
    website: str = Field(default="", max_length=2000)
    product: str = Field(default="", max_length=200)
    fit: Fit = "unknown"
    email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=80)
    whatsapp: str = Field(default="", max_length=80)
    instagram: str = Field(default="", max_length=2000)
    contact_person: str = Field(default="", max_length=200)
    city: str = Field(default="", max_length=120)
    target_city: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=80)
    status: Status = "research"
    notes: str = Field(default="", max_length=10000)
    name_tr: str = Field(default="", max_length=1000)
    product_tr: str = Field(default="", max_length=1000)
    evidence_tr: str = Field(default="", max_length=8000)
    supplier_evidence_tr: str = Field(default="", max_length=2000)
    notes_tr: str = Field(default="", max_length=20000)
    evidence: str = Field(default="", max_length=4000)
    source_url: str = Field(default="", max_length=2000)
    is_demo: bool = False
    buyer_type: Literal["unknown", "boutique", "multibrand", "concept", "retailer"] = "unknown"
    opportunity: Literal["unknown", "potential", "multibrand", "supplier_invitation"] = "unknown"
    priority: int = Field(default=0, ge=0, le=100)
    reasons: list[str] = Field(default_factory=list, max_length=12)
    assessment: Literal["unreviewed", "search", "website"] = "unreviewed"
    assessed_at: str = Field(default="", max_length=60)
    supplier_evidence: str = Field(default="", max_length=1000)
    supplier_source: str = Field(default="", max_length=2000)
    discovery_mode: str = Field(default="", max_length=30)
    sources: list[dict[str, str]] = Field(default_factory=list, max_length=20)

    @field_validator("website", "instagram", "source_url", "supplier_source")
    @classmethod
    def check_url(cls, v):
        return public_url(v)

    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        if v and not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", v):
            raise ValueError("Geçerli e-posta adresi girin.")
        return v

    @field_validator("reasons")
    @classmethod
    def check_reasons(cls, values):
        if any(len(v) > 500 for v in values):
            raise ValueError("Değerlendirme nedeni çok uzun.")
        return values

    @field_validator("sources")
    @classmethod
    def check_sources(cls, sources):
        for source in sources:
            if set(source) - {"url", "field", "value", "checked_at"} or any(len(v) > 4000 for v in source.values()):
                raise ValueError("Geçersiz kaynak.")
            source["url"] = public_url(source.get("url", ""))
        return sources


class LeadUpdate(BaseModel):
    lead: Lead
    version: int = Field(ge=1)


class EnrichRequest(BaseModel):
    url: str
    product: str = Field(default="", max_length=200)

    @field_validator("url")
    @classmethod
    def check_url(cls, v):
        if not v:
            raise ValueError("Web sitesi gerekli.")
        return public_url(v)
