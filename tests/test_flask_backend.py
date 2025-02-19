# pylint: disable=line-too-long, missing-module-docstring, missing-function-docstring

import os
import json
import socket
import threading
from unittest import TestCase
from unittest.mock import patch, MagicMock
import ffmpeg
from sqlalchemy.exc import OperationalError
import mock_kodi_modules
from paths import output_path, qr_path
from flask_backend import (
    app,
    get_bitrate,
    player,
    gen_mp4,
    address_available,
    wait_for_address_release,
    run_server,
    generate_qr_code_link
)


class TestAddressChecks(TestCase):
    @classmethod
    def setUpClass(cls):
        # Open a socket on a random port, save port to use in tests
        cls.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.s.bind(('127.0.0.1', 0))
        cls.used_port = cls.s.getsockname()[1]
        cls.s.listen(1)

    @classmethod
    def tearDownClass(cls):
        # Release port
        cls.s.close()

    def test_address_available(self):
        # Should return True for unused port
        self.assertTrue(address_available('0.0.0.0', 8888))
        # Should return False for used port
        self.assertFalse(address_available('0.0.0.0', self.used_port))

    def test_wait_for_address_release(self):
        # Should return True immediately for available port
        self.assertTrue(wait_for_address_release('0.0.0.0', 8888, 5))
        # Should return False after timeout seconds (5) for used port
        self.assertFalse(wait_for_address_release('0.0.0.0', self.used_port, 5))


class TestRunServer(TestCase):
    @classmethod
    def setUpClass(cls):
        # Open a socket on a random port, save port to use in tests
        cls.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.s.bind(('127.0.0.1', 0))
        cls.used_port = cls.s.getsockname()[1]
        cls.s.listen(1)

    @classmethod
    def tearDownClass(cls):
        # Release port
        cls.s.close()

    def test_run_server(self):
        # Get number of running threads before starting server
        threads_before = len(threading.enumerate())

        # Create mock getSettings that returns available address + autodelete enabled
        def mock_get_settings(setting):
            if setting == 'flask_host':
                return '0.0.0.0'
            if setting == 'flask_port':
                return '8888'
            if setting == 'autodelete':
                return 'true'
            return None

        # Mock methods called by run_server to confirm they were called
        with patch('flask_backend.autodelete', MagicMock()) as mock_autodelete, \
             patch('flask_backend.generate_qr_code_link', MagicMock()) as mock_gen_qr, \
             patch('flask_backend.address_unavailable_error', MagicMock()) as mock_addr_error, \
             patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:

            # Apply mock getSettings from above
            mock_addon.return_value.getSetting = mock_get_settings

            # Start server, confirm return value is not None
            server = run_server(timeout=1)
            self.assertIsNotNone(server)

            # Confirm that autodelete and generate_qr_code_link were called
            self.assertTrue(mock_autodelete.called)
            self.assertTrue(mock_gen_qr.called)

            # Confirm that address_unavailable_error was NOT called
            self.assertFalse(mock_addr_error.called)

        # Confirm that a new thread was created
        self.assertEqual(len(threading.enumerate()), threads_before + 1)

        # Close the server, confirm new thread stops
        server.shutdown()
        server.server_close()
        self.assertEqual(len(threading.enumerate()), threads_before)

    def test_run_server_autodelete_disabled(self):
        # Get number of running threads before starting server
        threads_before = len(threading.enumerate())

        # Create mock getSettings that returns available address + autodelete disabled
        def mock_get_settings(setting):
            if setting == 'flask_host':
                return '0.0.0.0'
            if setting == 'flask_port':
                return '8888'
            if setting == 'autodelete':
                return 'false'
            return None

        # Mock methods called by run_server to confirm they were called
        with patch('flask_backend.autodelete', MagicMock()) as mock_autodelete, \
             patch('flask_backend.generate_qr_code_link', MagicMock()) as mock_gen_qr, \
             patch('flask_backend.address_unavailable_error', MagicMock()) as mock_addr_error, \
             patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:

            # Apply mock getSettings from above
            mock_addon.return_value.getSetting = mock_get_settings

            # Start server, confirm return value is not None
            server = run_server(timeout=1)
            self.assertIsNotNone(server)

            # Confirm that autodelete and generate_qr_code_link was called
            self.assertTrue(mock_gen_qr.called)

            # Confirm that address_unavailable_error and autodelete were NOT called
            self.assertFalse(mock_addr_error.called)
            self.assertFalse(mock_autodelete.called)

        # Confirm that a new thread was created
        self.assertEqual(len(threading.enumerate()), threads_before + 1)

        # Close the server, confirm new thread stops
        server.shutdown()
        server.server_close()
        self.assertEqual(len(threading.enumerate()), threads_before)

    def test_run_server_address_unavailable(self):
        # Get number of running threads before starting server
        threads_before = len(threading.enumerate())

        # Create mock getSettings that returns unavailable address
        def mock_get_settings(setting):
            if setting == 'flask_host':
                return '0.0.0.0'
            if setting == 'flask_port':
                return self.used_port
            return None

        # Mock methods called by run_server to confirm they were NOT called
        with patch('flask_backend.autodelete', MagicMock()) as mock_autodelete, \
             patch('flask_backend.generate_qr_code_link', MagicMock()) as mock_gen_qr, \
             patch('flask_backend.address_unavailable_error', MagicMock()) as mock_addr_error, \
             patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:

            # Apply mock getSettings from above
            mock_addon.return_value.getSetting = mock_get_settings

            # Start server, confirm return value is None
            server = run_server(timeout=1)
            self.assertIsNone(server)

            # Confirm that autodelete and generate_qr_code_link were NOT called
            self.assertFalse(mock_autodelete.called)
            self.assertFalse(mock_gen_qr.called)

            # Confirm that address_unavailable_error was called
            self.assertTrue(mock_addr_error.called)

        # Confirm no new thread was created
        self.assertEqual(len(threading.enumerate()), threads_before)


class TestGenerateQrCodeLink(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Delete generated image
        os.remove(qr_path)

    def test_generate_qr_code_link(self):
        # Confirm output image does not exist
        self.assertFalse(os.path.exists(qr_path))
        # Generate QR code, confirm path exists
        generate_qr_code_link('123.45.67.89', 8888)
        self.assertTrue(os.path.exists(qr_path))


class TestEndpoints(TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_get_playtime(self):
        # Mock endpoint to return 123 seconds
        with patch.object(player, 'getTime', return_value=123):
            response = self.app.get('/get_playtime')
            # Confirm contents and status code
            self.assertEqual(response.get_json(), {'playtime': 123})
            self.assertEqual(response.status_code, 200)

    def test_get_playtime_nothing_playing(self):
        # Mock endpoint to simulate nothing playing
        with patch.object(player, 'getTime', side_effect=RuntimeError):
            response = self.app.get('/get_playtime')
            # Confirm contents and status code
            self.assertEqual(response.get_json(), {'error': 'Nothing playing'})
            self.assertEqual(response.status_code, 500)

    def test_get_playing_now_tv(self):
        # Create mock video_info_tag simulating TV show playing
        mock_video_info_tag = MagicMock()
        mock_video_info_tag.getMediaType.return_value = "episode"
        mock_video_info_tag.getTVShowTitle.return_value = "Show Name"
        mock_video_info_tag.getEpisode.return_value = "1"
        mock_video_info_tag.getSeason.return_value = "1"
        mock_video_info_tag.getTitle.return_value = "Episode Name"

        # Mock player object to return the mocked video_info_tag
        with patch.object(player, 'getVideoInfoTag', return_value=mock_video_info_tag):
            response = self.app.get('/get_playing_now')
            # Confirm contents and status code
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {
                "title": "Episode Name",
                "subtext": "Show Name - Season 1 - Episode 1"
            })

    def test_get_playing_now_movie(self):
        # Create mock video_info_tag simulating Movie playing
        mock_video_info_tag = MagicMock()
        mock_video_info_tag.getMediaType.return_value = "movie"
        mock_video_info_tag.getTitle.return_value = "Movie Name"

        # Mock player object to return the mocked video_info_tag
        with patch.object(player, 'getVideoInfoTag', return_value=mock_video_info_tag):
            response = self.app.get('/get_playing_now')
            # Confirm contents and status code
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {
                "title": "Movie Name",
                "subtext": ""
            })

    def test_get_playing_now_nothing(self):
        # Create mock video_info_tag simulating nothing playing
        mock_video_info_tag = MagicMock()
        mock_video_info_tag.getMediaType.side_effect = RuntimeError

        # Mock player object to return the mocked video_info_tag
        with patch.object(player, 'getVideoInfoTag', return_value=mock_video_info_tag):
            response = self.app.get('/get_playing_now')
            # Confirm contents and status code
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {
                "title": "Nothing",
                "subtext": ""
            })

    def test_submit(self):
        # Create mock video_info_tag simulating TV show playing
        mock_video_info_tag = MagicMock()
        mock_video_info_tag.getTVShowTitle.return_value = "Show Name"
        mock_video_info_tag.getTitle.return_value = "Episode Name"

        # Create mock request payload
        payload = json.dumps({'startTime': '23.4567'})

        # Mock player object methods to return the mocked video_info_tag, current playtime
        # Mock gen_mp4 to return True, mock log_generated_file to confirm correct args
        # Mock xbmc.executeJSONRPC (used to check audio track) to simulate first track
        with patch.object(player, 'getVideoInfoTag', return_value=mock_video_info_tag), \
             patch.object(player, 'getTime', return_value=123.4567), \
             patch.object(player, 'getPlayingFile', return_value='/path/to/source.mp4'), \
             patch('flask_backend.gen_mp4', return_value=True), \
             patch('flask_backend.log_generated_file', MagicMock()) as mock_log_generated_file, \
             patch('flask_backend.xbmc.executeJSONRPC', return_value='{"result": {"currentaudiostream": {"index": 0}}}'):

            response = self.app.post(
                '/submit',
                data=payload,
                content_type='application/json'
            )
            # Confirm status code, confirm response contains 20 character random filename
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(type(data), dict)
            self.assertEqual(len(data['filename']), 20)

            # Confirm log_generated_file was called with correct arguments
            self.assertTrue(mock_log_generated_file.called_once)
            mock_log_generated_file.assert_called_with(
                '/path/to/source.mp4',
                0,
                '23.4567',
                '100.0',
                data['filename'].replace('.mp4', ''),
                'Show Name',
                'Episode Name'
            )

    def test_submit_sql_error(self):
        # Create mock video_info_tag simulating TV show playing
        mock_video_info_tag = MagicMock()
        mock_video_info_tag.getTVShowTitle.return_value = "Show Name"
        mock_video_info_tag.getTitle.return_value = "Episode Name"

        # Create mock request payload
        payload = json.dumps({'startTime': '23.4567'})

        # Mock player object methods to return the mocked video_info_tag, current playtime
        # Mock gen_mp4 to return True, mock log_generated_file to simulate locked database
        # Mock xbmc.executeJSONRPC (used to check audio track) to simulate first track
        with patch.object(player, 'getVideoInfoTag', return_value=mock_video_info_tag), \
             patch.object(player, 'getTime', return_value=123.4567), \
             patch.object(player, 'getPlayingFile', return_value='/path/to/source.mp4'), \
             patch('flask_backend.gen_mp4', return_value=True), \
             patch('flask_backend.log_generated_file', side_effect=OperationalError("", "", "Database locked")), \
             patch('flask_backend.xbmc.executeJSONRPC', return_value='{"result": {"currentaudiostream": {"index": 0}}}'):

            response = self.app.post(
                '/submit',
                data=payload,
                content_type='application/json'
            )
            # Confirm status code and error response
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.get_json(),
                {'error': 'Unable to generate file, see Kodi logs for details'}
            )

    def test_submit_nothing_playing(self):
        # Create mock request payload
        payload = json.dumps({'startTime': '23.4567'})

        # Mock player object to raise error (simulate nothing playing)
        with patch.object(player, 'getTime', side_effect=RuntimeError("Nothing is playing")):
            response = self.app.post('/submit', data=payload, content_type='application/json')
            # Confirm status code and error response
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.get_json(),
                {'error': 'Unable to generate file, see Kodi logs for details'}
            )

    def test_regenerate(self):
        # Create mock request payload
        payload = json.dumps({'filename': 'target_file'})

        # Create mock ORM entry
        mock_entry = MagicMock()
        mock_entry.source = "/path/to/source.mp4"
        mock_entry.start_time = "100"
        mock_entry.duration = "10"
        mock_entry.show_name = "Show Name"
        mock_entry.episode_name = "Episode Name"

        # Mock get_orm_entry to return mocked entry
        with patch('flask_backend.get_orm_entry', return_value=mock_entry), \
             patch('flask_backend.gen_mp4', return_value=True), \
             patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:

            # Mock quality setting to 20 MB/min
            mock_addon.return_value.getSetting.return_value = '20'

            response = self.app.post(
                '/regenerate',
                data=payload,
                content_type='application/json'
            )
            # Confirm status code and response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.get_json()['filename'],
                'target_file.mp4'
            )

    def test_regenerate_sql_error(self):
        # Create mock request payload
        payload = json.dumps({'filename': 'target_file'})

        # Mock player object to raise error (simulate database issue)
        with patch('flask_backend.get_orm_entry', side_effect=OperationalError("", "", "Database locked")):
            response = self.app.post(
                '/regenerate',
                data=payload,
                content_type='application/json'
            )
            # Confirm status code and error response
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.get_json(),
                {'error': 'Unable to generate file, see Kodi logs for details'}
            )

    def test_download(self):
        with patch('flask_backend.send_from_directory') as mock_send_from_directory:
            # Create mock filename and contents
            filename = 'clip.mp4'
            mock_send_from_directory.return_value = 'contents'

            # Send request, confirm status code and file contents
            response = self.app.get(f'/download/{filename}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode('utf-8'), 'contents')

            # Confirm mock called with correct args
            mock_send_from_directory.assert_called_once_with(output_path, filename, as_attachment=True)

    def test_get_history(self):
        # Create mock history JSON
        mock_history = {
            '2023-09-22_23:24:31.218942': 'output1.mp4',
            '2023-09-22_23:24:33.295994': 'output2.mp4'
        }

        # Mock database function to return mocked history
        with patch('flask_backend.load_history_json', return_value=mock_history):
            # Send request, confirm status code and JSON
            response = self.app.get('/get_history')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), mock_history)

    def test_search_history(self):
        # Create mock history JSON
        mock_history = {
            '2023-09-22_23:24:31.218942': 'output1.mp4',
            '2023-09-22_23:24:33.295994': 'output2.mp4'
        }

        # Mock database function to return mocked history
        with patch('flask_backend.load_history_search_results', return_value=mock_history):
            # Send request, confirm status code and JSON
            response = self.app.post(
                '/search_history',
                data=json.dumps({'query': 'search'}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), mock_history)

    def test_delete(self):
        # Mock database function to do nothing
        with patch('flask_backend.delete_entry'):
            # Send request, confirm status code and JSON
            response = self.app.post(
                '/delete',
                data=json.dumps({'filename': 'file.mp4'}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {'deleted': 'file.mp4'})

    def test_rename(self):
        # Create mock request payload with trailing whitespace
        payload = json.dumps({'old': 'original.mp4', 'new': 'new_name '})

        # Mock database function to do nothing, mock is_duplicate to return False
        with patch('flask_backend.rename_entry'), \
             patch('flask_backend.is_duplicate', return_value=False):

            # Send request, confirm status code and JSON, confirm trailing whitespace removed
            response = self.app.post(
                '/rename',
                data=payload,
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.get_json(),
                {'filename': 'new_name.mp4'}
            )

    def test_rename_duplicate(self):
        # Create mock request payload
        payload = json.dumps({'old': 'original.mp4', 'new': 'new_name'})

        # Mock database function to do nothing, mock is_duplicate to return True
        with patch('flask_backend.rename_entry'), \
             patch('flask_backend.is_duplicate', return_value=True):

            # Send request, confirm status code and JSON
            response = self.app.post(
                '/rename',
                data=payload,
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(
                response.get_json(),
                {'error': 'File named new_name.mp4 already exists'}
            )


class TestGetBitrate(TestCase):
    def test_get_bitrate(self):
        with patch('xbmcaddon.Addon', return_value=MagicMock()) as mock_addon:
            # Mock quality setting to 20 MB/min
            mock_addon.return_value.getSetting.return_value = '20'
            # Confirm correct bitrate
            self.assertEqual(get_bitrate(), 2796202)


class TestGenMp4(TestCase):
    def test_generate(self):
        # Mock ffmpeg, mock get_bitrate to return arbitrary value
        with patch('flask_backend.get_bitrate', return_value=2796202), \
             patch('flask_backend.ffmpeg', MagicMock) as mock_ffmpeg:

            # Mock ffmpeg.probe to return a lower bitrate than get_bitrate
            mock_ffmpeg.probe = MagicMock(return_value={'format': {'bit_rate': '1500000'}})
            # Mock methods to confirm called with correct args
            mock_ffmpeg.input = MagicMock()
            mock_ffmpeg.output = MagicMock()
            mock_ffmpeg.run = MagicMock()

            # Call function with mock arguments, should return True
            self.assertTrue(gen_mp4(
                '/path/to/source.mp4',
                0,
                '23.4567',
                '100.0',
                'output'
            ))

            # Confirm correct args passed to ffmpeg methods
            mock_ffmpeg.input.assert_called_with('/path/to/source.mp4')
            mock_ffmpeg.output.assert_called_with(
                os.path.join(output_path, 'output.mp4'),
                ss='23.4567',
                t='100.0',
                vcodec="libx264",
                b="1500000",
                acodec="aac",
                ac="2",
                map=['0:v:0', '0:a:0']
            )

    def test_generate_error(self):
        # Mock ffmpeg to raise exception, mock get_bitrate and ffmpeg.probe to return arbitrary values
        with patch('flask_backend.get_bitrate', return_value=2796202), \
             patch('flask_backend.ffmpeg.probe', return_value={'format': {'bit_rate': '1500000'}}), \
             patch('flask_backend.ffmpeg.input', side_effect=ffmpeg.Error(cmd="", stdout="", stderr="".encode())):

            # Call function with mock arguments, should return False
            self.assertFalse(gen_mp4(
                '/path/to/source.mp4',
                0,
                '23.4567',
                '100.0',
                'output'
            ))
