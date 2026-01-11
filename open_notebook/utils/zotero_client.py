"""
Zotero client wrapper for fetching documents via pyzotero.
"""

import os
from typing import Any, Dict, List, Optional

from loguru import logger
from pyzotero import zotero


class ZoteroClient:
    """
    Wrapper around pyzotero for fetching and searching Zotero documents.
    """

    def __init__(
        self,
        library_id: Optional[str] = None,
        library_type: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Zotero client.

        Args:
            library_id: Zotero user ID or group ID
            library_type: 'user' or 'group'
            api_key: Zotero API key
        """
        self.library_id = library_id or os.getenv("ZOTERO_USER_ID") or os.getenv("ZOTERO_GROUP_ID")
        self.library_type = library_type or os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        self.api_key = api_key or os.getenv("ZOTERO_API_KEY")

        if not self.library_id:
            raise ValueError(
                "Zotero library ID is required. Set ZOTERO_USER_ID or ZOTERO_GROUP_ID environment variable."
            )
        if not self.api_key:
            raise ValueError(
                "Zotero API key is required. Set ZOTERO_API_KEY environment variable."
            )
        
        # Validate library_type
        if self.library_type not in ("user", "group"):
            raise ValueError(
                f"Invalid library_type: {self.library_type}. Must be 'user' or 'group'."
            )

        self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)
        logger.debug(
            f"Initialized Zotero client for {self.library_type} library"
        )

    def search(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search Zotero library.

        Args:
            query: Search query text
            search_fields: Controls search mode. If 'fulltext' is included, performs full-text search.
                          Otherwise, performs quick search in title, creator, and year fields.
                          Note: Individual field filtering is not supported - only fulltext vs. quick search.
            limit: Maximum number of results to return

        Returns:
            List of Zotero items matching the search query
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Default to searching title and creator
        if search_fields is None:
            search_fields = ["title", "creator"]

        logger.info(
            f"Searching Zotero library with query: '{query}' in fields: {search_fields}"
        )

        try:
            # Zotero search uses different methods based on field
            if "fulltext" in search_fields:
                # Full-text search
                logger.debug("Performing full-text search")
                results = self.zot.everything(self.zot.fulltext_item(query))
                # Apply limit to fulltext results
                results = results[:limit]
            else:
                # Quick search in title, creator, and year
                # Note: The 'q' parameter searches in title, creator, and year fields
                # The search_fields parameter only controls whether fulltext search is used
                logger.debug("Performing quick search in title, creator, and year")
                results = self.zot.items(q=query, limit=limit)

            logger.info(f"Found {len(results)} items in Zotero library")
            return results

        except Exception as e:
            logger.error(f"Error searching Zotero library: {e}")
            raise

    def get_item(self, item_key: str) -> Dict[str, Any]:
        """
        Get a specific Zotero item by key.

        Args:
            item_key: Zotero item key

        Returns:
            Zotero item data
        """
        if not item_key or not item_key.strip():
            raise ValueError("Zotero item_key cannot be empty")
        
        item_key = item_key.strip()
        logger.info(f"Fetching Zotero item: {item_key}")
        try:
            item = self.zot.item(item_key)
            return item
        except Exception as e:
            logger.error(f"Error fetching Zotero item {item_key}: {e}")
            raise

    def get_item_attachment_url(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Get URL of the primary attachment for a Zotero item.

        Args:
            item: Zotero item data

        Returns:
            URL of the attachment, or None if no attachment found
        """
        try:
            # Get item key
            item_key = item.get("key")
            if not item_key:
                return None

            # Get children (attachments, notes)
            children = self.zot.children(item_key)

            # Find first PDF or document attachment
            for child in children:
                child_data = child.get("data", {})
                if child_data.get("itemType") == "attachment":
                    content_type = child_data.get("contentType", "")
                    if "pdf" in content_type.lower() or "document" in content_type.lower():
                        # Check if it's a link attachment
                        link_mode = child_data.get("linkMode")
                        if link_mode in ["linked_url", "imported_url"]:
                            url = child_data.get("url")
                            if url:
                                logger.debug(f"Found attachment URL: {url}")
                                return url

            logger.debug(f"No attachment URL found for item {item_key}")
            return None

        except Exception as e:
            logger.warning(f"Error getting attachment URL: {e}")
            return None

    def format_item_for_source(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Zotero item data for Open Notebook source creation.

        Args:
            item: Zotero item data

        Returns:
            Dictionary with formatted source data
        """
        data = item.get("data", {})

        # Extract title
        title = data.get("title", "Untitled")

        # Extract creators (authors, editors, etc.)
        creators = data.get("creators", [])
        authors = []
        for creator in creators:
            first_name = creator.get("firstName", "")
            last_name = creator.get("lastName", "")
            name = creator.get("name", "")  # For organizations
            
            if name:
                authors.append(name)
            elif first_name or last_name:
                authors.append(f"{first_name} {last_name}".strip())

        # Extract abstract/content
        abstract = data.get("abstractNote", "")

        # Extract metadata
        metadata = {
            "item_type": data.get("itemType", ""),
            "authors": authors,
            "publication": data.get("publicationTitle", ""),
            "year": data.get("date", ""),
            "doi": data.get("DOI", ""),
            "url": data.get("url", ""),
            "tags": [tag.get("tag", "") for tag in data.get("tags", [])],
        }

        # Build content text from metadata
        content_parts = [f"# {title}\n"]
        
        if authors:
            content_parts.append(f"**Authors:** {', '.join(authors)}\n")
        
        if metadata["year"]:
            content_parts.append(f"**Year:** {metadata['year']}\n")
        
        if metadata["publication"]:
            content_parts.append(f"**Publication:** {metadata['publication']}\n")
        
        if metadata["doi"]:
            content_parts.append(f"**DOI:** {metadata['doi']}\n")
        
        if metadata["url"]:
            content_parts.append(f"**URL:** {metadata['url']}\n")
        
        if abstract:
            content_parts.append(f"\n## Abstract\n\n{abstract}\n")

        content = "\n".join(content_parts)

        # Try to get attachment URL
        attachment_url = self.get_item_attachment_url(item)

        return {
            "title": title,
            "content": content,
            "url": attachment_url or metadata.get("url"),
            "metadata": metadata,
            "zotero_key": item.get("key"),
        }


def get_zotero_client() -> ZoteroClient:
    """
    Get a configured Zotero client instance.

    Returns:
        ZoteroClient instance

    Raises:
        ValueError: If Zotero credentials are not configured
    """
    return ZoteroClient()
