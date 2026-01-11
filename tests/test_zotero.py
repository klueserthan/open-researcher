"""
Unit tests for the Zotero integration.

This test suite focuses on testing the ZoteroClient class and related functionality
with mocked pyzotero responses to ensure proper error handling, data processing,
and validation without making actual API calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from open_notebook.utils.zotero_client import ZoteroClient, get_zotero_client


# ============================================================================
# TEST SUITE 1: ZoteroClient Initialization
# ============================================================================


class TestZoteroClientInitialization:
    """Test suite for ZoteroClient initialization and validation."""

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters provided."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero') as mock_zotero:
            client = ZoteroClient(
                library_id="12345",
                library_type="user",
                api_key="test_api_key"
            )
            
            assert client.library_id == "12345"
            assert client.library_type == "user"
            assert client.api_key == "test_api_key"
            mock_zotero.assert_called_once_with("12345", "user", "test_api_key")

    def test_init_with_whitespace_trimming(self):
        """Test that whitespace is trimmed from parameters."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero') as mock_zotero:
            client = ZoteroClient(
                library_id="  12345  ",
                library_type="  user  ",
                api_key="  test_api_key  "
            )
            
            assert client.library_id == "12345"
            assert client.library_type == "user"
            assert client.api_key == "test_api_key"

    def test_init_missing_library_id(self):
        """Test initialization fails without library_id."""
        with pytest.raises(ValueError, match="Zotero library ID is required"):
            ZoteroClient(library_id=None, library_type="user", api_key="test_key")

    def test_init_missing_api_key(self):
        """Test initialization fails without api_key."""
        with pytest.raises(ValueError, match="Zotero API key is required"):
            ZoteroClient(library_id="12345", library_type="user", api_key=None)

    def test_init_invalid_library_type(self):
        """Test initialization fails with invalid library_type."""
        with pytest.raises(ValueError, match="Invalid library_type"):
            ZoteroClient(library_id="12345", library_type="invalid", api_key="test_key")

    def test_init_valid_library_types(self):
        """Test initialization succeeds with valid library types."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero'):
            # Test 'user' type
            client = ZoteroClient(library_id="12345", library_type="user", api_key="test_key")
            assert client.library_type == "user"
            
            # Test 'group' type
            client = ZoteroClient(library_id="12345", library_type="group", api_key="test_key")
            assert client.library_type == "group"

    @patch.dict('os.environ', {'ZOTERO_USER_ID': '12345', 'ZOTERO_API_KEY': 'env_key'})
    def test_init_from_environment_variables(self):
        """Test initialization from environment variables."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero') as mock_zotero:
            client = ZoteroClient()
            
            assert client.library_id == "12345"
            assert client.api_key == "env_key"
            assert client.library_type == "user"  # Default
            mock_zotero.assert_called_once()

    @patch.dict('os.environ', {'ZOTERO_GROUP_ID': '67890', 'ZOTERO_API_KEY': 'env_key', 'ZOTERO_LIBRARY_TYPE': 'group'})
    def test_init_from_environment_group_library(self):
        """Test initialization with group library from environment."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero') as mock_zotero:
            client = ZoteroClient()
            
            assert client.library_id == "67890"
            assert client.library_type == "group"
            assert client.api_key == "env_key"


# ============================================================================
# TEST SUITE 2: Search Functionality
# ============================================================================


class TestZoteroClientSearch:
    """Test suite for ZoteroClient search functionality."""

    def setup_method(self):
        """Setup mock client for each test."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero'):
            self.client = ZoteroClient(
                library_id="12345",
                library_type="user",
                api_key="test_key"
            )

    def test_search_empty_query(self):
        """Test search fails with empty query."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            self.client.search("")

    def test_search_whitespace_only_query(self):
        """Test search fails with whitespace-only query."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            self.client.search("   ")

    def test_search_quick_search_default(self):
        """Test quick search with default parameters."""
        mock_items = [
            {"key": "ABC123", "data": {"title": "Test Article"}},
            {"key": "DEF456", "data": {"title": "Another Article"}}
        ]
        self.client.zot.items = Mock(return_value=mock_items)
        
        results = self.client.search("machine learning")
        
        assert len(results) == 2
        assert results[0]["key"] == "ABC123"
        self.client.zot.items.assert_called_once_with(q="machine learning", limit=100)

    def test_search_quick_search_with_limit(self):
        """Test quick search with custom limit."""
        mock_items = [{"key": "ABC123", "data": {"title": "Test"}}]
        self.client.zot.items = Mock(return_value=mock_items)
        
        results = self.client.search("test query", limit=50)
        
        self.client.zot.items.assert_called_once_with(q="test query", limit=50)

    def test_search_fulltext_search(self):
        """Test fulltext search mode."""
        mock_items = [{"key": "ABC123", "data": {"title": "Test"}}]
        self.client.zot.fulltext_item = Mock(return_value=[])
        self.client.zot.everything = Mock(return_value=mock_items)
        
        results = self.client.search("test query", search_fields=["fulltext"])
        
        assert len(results) == 1
        self.client.zot.fulltext_item.assert_called_once_with("test query")
        self.client.zot.everything.assert_called_once()

    def test_search_fulltext_with_limit(self):
        """Test fulltext search respects limit."""
        mock_items = [
            {"key": f"ITEM{i}", "data": {"title": f"Article {i}"}}
            for i in range(150)
        ]
        self.client.zot.fulltext_item = Mock(return_value=[])
        self.client.zot.everything = Mock(return_value=mock_items)
        
        results = self.client.search("test", search_fields=["fulltext"], limit=50)
        
        # Should be limited to 50 items
        assert len(results) == 50

    def test_search_invalid_fields_warning(self, caplog):
        """Test warning is logged for invalid search fields."""
        mock_items = []
        self.client.zot.items = Mock(return_value=mock_items)
        
        with caplog.at_level("WARNING"):
            self.client.search("test", search_fields=["invalid", "field", "title"])
        
        # Check warning was logged
        assert "Unrecognized search_fields" in caplog.text
        assert "invalid" in caplog.text

    def test_search_exception_handling(self):
        """Test search handles exceptions from pyzotero."""
        self.client.zot.items = Mock(side_effect=Exception("API Error"))
        
        with pytest.raises(Exception, match="API Error"):
            self.client.search("test query")


# ============================================================================
# TEST SUITE 3: Item Fetching
# ============================================================================


class TestZoteroClientGetItem:
    """Test suite for ZoteroClient get_item functionality."""

    def setup_method(self):
        """Setup mock client for each test."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero'):
            self.client = ZoteroClient(
                library_id="12345",
                library_type="user",
                api_key="test_key"
            )

    def test_get_item_success(self):
        """Test successful item retrieval."""
        mock_item = {"key": "ABC123", "data": {"title": "Test Article"}}
        self.client.zot.item = Mock(return_value=mock_item)
        
        result = self.client.get_item("ABC123")
        
        assert result == mock_item
        self.client.zot.item.assert_called_once_with("ABC123")

    def test_get_item_empty_key(self):
        """Test get_item fails with empty key."""
        with pytest.raises(ValueError, match="Zotero item_key cannot be empty"):
            self.client.get_item("")

    def test_get_item_whitespace_key(self):
        """Test get_item fails with whitespace-only key."""
        with pytest.raises(ValueError, match="Zotero item_key cannot be empty"):
            self.client.get_item("   ")

    def test_get_item_whitespace_trimming(self):
        """Test whitespace is trimmed from item key."""
        mock_item = {"key": "ABC123", "data": {"title": "Test"}}
        self.client.zot.item = Mock(return_value=mock_item)
        
        result = self.client.get_item("  ABC123  ")
        
        self.client.zot.item.assert_called_once_with("ABC123")

    def test_get_item_not_found(self):
        """Test get_item handles item not found."""
        self.client.zot.item = Mock(side_effect=Exception("Item not found"))
        
        with pytest.raises(Exception, match="Item not found"):
            self.client.get_item("NONEXISTENT")


# ============================================================================
# TEST SUITE 4: Author Extraction
# ============================================================================


class TestZoteroClientExtractAuthors:
    """Test suite for extract_authors_from_creators functionality."""

    def setup_method(self):
        """Setup mock client for each test."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero'):
            self.client = ZoteroClient(
                library_id="12345",
                library_type="user",
                api_key="test_key"
            )

    def test_extract_authors_standard_format(self):
        """Test extracting authors with first and last names."""
        creators = [
            {"firstName": "John", "lastName": "Doe"},
            {"firstName": "Jane", "lastName": "Smith"}
        ]
        
        authors = self.client.extract_authors_from_creators(creators)
        
        assert len(authors) == 2
        assert authors[0] == {"name": "John Doe", "first_name": "John", "last_name": "Doe"}
        assert authors[1] == {"name": "Jane Smith", "first_name": "Jane", "last_name": "Smith"}

    def test_extract_authors_organization_name(self):
        """Test extracting organizational authors."""
        creators = [
            {"name": "MIT Press"},
            {"firstName": "John", "lastName": "Doe"}
        ]
        
        authors = self.client.extract_authors_from_creators(creators)
        
        assert len(authors) == 2
        assert authors[0] == {"name": "MIT Press", "first_name": "", "last_name": ""}
        assert authors[1] == {"name": "John Doe", "first_name": "John", "last_name": "Doe"}

    def test_extract_authors_missing_first_name(self):
        """Test extracting authors with only last name."""
        creators = [
            {"lastName": "Einstein"},
            {"firstName": "Marie", "lastName": ""}
        ]
        
        authors = self.client.extract_authors_from_creators(creators)
        
        assert len(authors) == 2
        assert authors[0] == {"name": "Einstein", "first_name": "", "last_name": "Einstein"}
        assert authors[1] == {"name": "Marie", "first_name": "Marie", "last_name": ""}

    def test_extract_authors_empty_list(self):
        """Test extracting from empty creators list."""
        authors = self.client.extract_authors_from_creators([])
        
        assert authors == []

    def test_extract_authors_invalid_entries(self):
        """Test extracting authors skips invalid entries."""
        creators = [
            {"firstName": "John", "lastName": "Doe"},
            "invalid_string",
            None,
            {"firstName": "Jane", "lastName": "Smith"}
        ]
        
        authors = self.client.extract_authors_from_creators(creators)
        
        assert len(authors) == 2
        assert authors[0]["name"] == "John Doe"
        assert authors[1]["name"] == "Jane Smith"

    def test_extract_authors_whitespace_handling(self):
        """Test author extraction handles whitespace correctly."""
        creators = [
            {"firstName": "  John  ", "lastName": "  Doe  "},
            {"firstName": "", "lastName": "Smith"}
        ]
        
        authors = self.client.extract_authors_from_creators(creators)
        
        # Should strip whitespace in the combined name
        assert len(authors) == 2
        assert "John" in authors[0]["name"]
        assert "Doe" in authors[0]["name"]
        assert authors[1]["name"] == "Smith"


# ============================================================================
# TEST SUITE 5: Attachment URL Detection
# ============================================================================


class TestZoteroClientAttachmentURL:
    """Test suite for get_item_attachment_url functionality."""

    def setup_method(self):
        """Setup mock client for each test."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero'):
            self.client = ZoteroClient(
                library_id="12345",
                library_type="user",
                api_key="test_key"
            )

    def test_get_attachment_url_linked_url(self):
        """Test getting attachment URL with linked_url mode."""
        item = {"key": "ABC123"}
        children = [
            {
                "data": {
                    "itemType": "attachment",
                    "contentType": "application/pdf",
                    "linkMode": "linked_url",
                    "url": "https://example.com/paper.pdf"
                }
            }
        ]
        self.client.zot.children = Mock(return_value=children)
        
        url = self.client.get_item_attachment_url(item)
        
        assert url == "https://example.com/paper.pdf"

    def test_get_attachment_url_imported_file(self):
        """Test getting attachment URL with imported_file mode."""
        item = {"key": "ABC123"}
        children = [
            {
                "data": {
                    "itemType": "attachment",
                    "contentType": "application/pdf",
                    "linkMode": "imported_file",
                    "url": "https://example.com/file.pdf"
                }
            }
        ]
        self.client.zot.children = Mock(return_value=children)
        
        url = self.client.get_item_attachment_url(item)
        
        assert url == "https://example.com/file.pdf"

    def test_get_attachment_url_no_key(self):
        """Test attachment URL returns None when item has no key."""
        item = {}
        
        url = self.client.get_item_attachment_url(item)
        
        assert url is None

    def test_get_attachment_url_no_attachments(self):
        """Test attachment URL returns None when no attachments."""
        item = {"key": "ABC123"}
        self.client.zot.children = Mock(return_value=[])
        
        url = self.client.get_item_attachment_url(item)
        
        assert url is None

    def test_get_attachment_url_unsupported_link_mode(self):
        """Test attachment URL returns None for unsupported link modes."""
        item = {"key": "ABC123"}
        children = [
            {
                "data": {
                    "itemType": "attachment",
                    "contentType": "application/pdf",
                    "linkMode": "embedded_image",
                    "url": "https://example.com/image.pdf"
                }
            }
        ]
        self.client.zot.children = Mock(return_value=children)
        
        url = self.client.get_item_attachment_url(item)
        
        assert url is None

    def test_get_attachment_url_exception_handling(self):
        """Test attachment URL handles exceptions gracefully."""
        item = {"key": "ABC123"}
        self.client.zot.children = Mock(side_effect=Exception("API Error"))
        
        # Should return None instead of raising
        url = self.client.get_item_attachment_url(item)
        
        assert url is None


# ============================================================================
# TEST SUITE 6: Item Formatting
# ============================================================================


class TestZoteroClientFormatItem:
    """Test suite for format_item_for_source functionality."""

    def setup_method(self):
        """Setup mock client for each test."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero'):
            self.client = ZoteroClient(
                library_id="12345",
                library_type="user",
                api_key="test_key"
            )

    def test_format_item_complete_metadata(self):
        """Test formatting item with complete metadata."""
        item = {
            "key": "ABC123",
            "data": {
                "title": "Test Article",
                "creators": [
                    {"firstName": "John", "lastName": "Doe"}
                ],
                "abstractNote": "This is a test abstract.",
                "itemType": "journalArticle",
                "publicationTitle": "Test Journal",
                "volume": "42",
                "issue": "3",
                "date": "2023",
                "DOI": "10.1234/test",
                "ISBN": "978-3-16-148410-0",
                "url": "https://example.com",
                "tags": [{"tag": "machine learning"}, {"tag": "AI"}]
            }
        }
        self.client.zot.children = Mock(return_value=[])
        
        result = self.client.format_item_for_source(item)
        
        assert result["title"] == "Test Article"
        assert "Test Article" in result["content"]
        assert "John Doe" in result["content"]
        # Abstract should NOT be in content anymore
        assert "This is a test abstract" not in result["content"]
        # But should be in metadata
        assert result["metadata"]["abstract"] == "This is a test abstract."
        assert result["metadata"]["item_type"] == "journalArticle"
        assert result["metadata"]["publication"] == "Test Journal"
        assert result["metadata"]["volume"] == "42"
        assert result["metadata"]["issue"] == "3"
        assert result["metadata"]["doi"] == "10.1234/test"
        assert result["metadata"]["isbn"] == "978-3-16-148410-0"
        assert result["zotero_key"] == "ABC123"

    def test_format_item_missing_title(self):
        """Test formatting item with missing title."""
        item = {
            "key": "ABC123",
            "data": {}
        }
        self.client.zot.children = Mock(return_value=[])
        
        result = self.client.format_item_for_source(item)
        
        assert result["title"] == "Untitled"
        assert "Untitled" in result["content"]

    def test_format_item_with_attachment(self):
        """Test formatting item includes attachment URL."""
        item = {
            "key": "ABC123",
            "data": {
                "title": "Test Article"
            }
        }
        children = [
            {
                "data": {
                    "itemType": "attachment",
                    "contentType": "application/pdf",
                    "linkMode": "linked_url",
                    "url": "https://example.com/paper.pdf"
                }
            }
        ]
        self.client.zot.children = Mock(return_value=children)
        
        result = self.client.format_item_for_source(item)
        
        assert result["url"] == "https://example.com/paper.pdf"

    def test_format_item_no_abstract(self):
        """Test formatting item without abstract."""
        item = {
            "key": "ABC123",
            "data": {
                "title": "Test Article"
            }
        }
        self.client.zot.children = Mock(return_value=[])
        
        result = self.client.format_item_for_source(item)
        
        # Abstract should not be in content
        assert "Abstract" not in result["content"]
        # Empty abstract in metadata
        assert result["metadata"]["abstract"] == ""


# ============================================================================
# TEST SUITE 7: Factory Function
# ============================================================================


class TestGetZoteroClient:
    """Test suite for get_zotero_client factory function."""

    @patch.dict('os.environ', {'ZOTERO_USER_ID': '12345', 'ZOTERO_API_KEY': 'test_key'})
    def test_get_zotero_client_success(self):
        """Test factory function creates client successfully."""
        with patch('open_notebook.utils.zotero_client.zotero.Zotero'):
            client = get_zotero_client()
            
            assert isinstance(client, ZoteroClient)
            assert client.library_id == "12345"
            assert client.api_key == "test_key"

    @patch.dict('os.environ', {}, clear=True)
    def test_get_zotero_client_missing_credentials(self):
        """Test factory function fails without credentials."""
        with pytest.raises(ValueError, match="Zotero library ID is required"):
            get_zotero_client()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
