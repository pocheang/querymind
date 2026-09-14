from __future__ import annotations

from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    """Normalized search result item returned by all web search providers."""

    title: str = Field(default="", description="Webpage title")
    href: str = Field(default="", description="Webpage destination URL")
    body: str = Field(default="", description="Snippet or brief description of the page content")
    raw_content: str | None = Field(default=None, description="Optional full raw text content if fetched")
    score: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence or relevance score")
    published_date: str | None = Field(default=None, description="Publish date if available")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "href": self.href,
            "body": self.body,
            "raw_content": self.raw_content,
            "score": self.score,
            "published_date": self.published_date,
        }
