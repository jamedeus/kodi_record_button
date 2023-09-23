import sys
from unittest.mock import Mock


# Mock xbmc modules
sys.modules['xbmc'] = Mock()
sys.modules['xbmcgui'] = Mock()
sys.modules['xbmcaddon'] = Mock(Addon=Mock)


# Mock xbmcvfs methods
mock_xbmcvfs = Mock()
mock_xbmcvfs.translatePath.return_value = '.'
mock_xbmcvfs.exists.return_value = True
mock_xbmcvfs.mkdir.return_value = True
sys.modules['xbmcvfs'] = mock_xbmcvfs
