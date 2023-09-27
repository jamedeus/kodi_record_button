import sys
from unittest.mock import Mock


# Mock xbmc modules
sys.modules['xbmc'] = Mock()
sys.modules['xbmcgui'] = Mock()

# Mock getSettings to return SQLite (default to local database in tests)
# This is overridden with patch in tests that require another value
mock_addon = Mock()
mock_addon.return_value.getSetting.return_value = 'SQLite'
sys.modules['xbmcaddon'] = Mock(Addon=mock_addon)

# Mock xbmcvfs methods
mock_xbmcvfs = Mock()
mock_xbmcvfs.translatePath.return_value = '.'
mock_xbmcvfs.exists.return_value = True
mock_xbmcvfs.mkdir.return_value = True
sys.modules['xbmcvfs'] = mock_xbmcvfs
