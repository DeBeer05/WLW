from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from Scan.application.scan_use_cases import ScanUseCases
from Scan.application.background_scan_service import ScanService
from Scan.data_access.scan_repository import ScanRepository
from Scan.models import Device, ScanSession


class ScanApiViewTests(SimpleTestCase):
	def test_index_returns_status_payload(self):
		"""Index status."""
		with patch("Scan.presentation.api_views.scan_use_cases.index_status") as index_status:
			index_status.return_value = {
				"status": "info",
				"message": "ready",
			}

			response = self.client.get(reverse("scan:index"))

		self.assertEqual(response.status_code, 200)
		self.assertJSONEqual(response.content, {"status": "info", "message": "ready"})
		index_status.assert_called_once_with()

	def test_start_scan_uses_request_payload(self):
		"""Start scan payload."""
		with patch("Scan.presentation.api_views.scan_use_cases.start_scan") as start_scan:
			start_scan.return_value = {
				"status": "success",
				"scan_id": 10,
				"device_count": 1,
				"devices": {"AA": {"mac": "AA"}},
			}

			response = self.client.post(
				reverse("scan:start_scan"),
				data="{\"duration\": 8, \"port\": \"COM7\"}",
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["scan_id"], 10)
		start_scan.assert_called_once_with(duration=8, port="COM7")

	def test_start_scan_uses_defaults_when_body_is_empty(self):
		"""Start scan defaults."""
		with patch("Scan.presentation.api_views.scan_use_cases.start_scan") as start_scan:
			start_scan.return_value = {
				"status": "success",
				"scan_id": 11,
				"device_count": 0,
				"devices": {},
			}

			response = self.client.post(
				reverse("scan:start_scan"),
				data="",
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["device_count"], 0)
		start_scan.assert_called_once_with(duration=5, port="/dev/ttyS2")

	def test_start_scan_returns_error_payload_on_exception(self):
		"""Start scan error."""
		with patch("Scan.presentation.api_views.scan_use_cases.start_scan") as start_scan:
			start_scan.side_effect = RuntimeError("scanner unavailable")

			response = self.client.post(
				reverse("scan:start_scan"),
				data="{}",
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 500)
		self.assertJSONEqual(
			response.content,
			{"status": "error", "message": "scanner unavailable"},
		)

	def test_scan_history_returns_json_payload(self):
		"""History payload."""
		payload = {
			"status": "success",
			"scans": [{"id": 1, "device_count": 2}],
		}
		with patch("Scan.presentation.api_views.scan_use_cases.get_scan_history") as get_scan_history:
			get_scan_history.return_value = payload

			response = self.client.get(reverse("scan:scan_history"))

		self.assertEqual(response.status_code, 200)
		self.assertJSONEqual(response.content, payload)
		get_scan_history.assert_called_once_with()

	def test_scan_details_passes_route_parameter(self):
		"""Details route id."""
		payload = {
			"status": "success",
			"scan": {"id": 7, "device_count": 1, "devices": []},
		}
		with patch("Scan.presentation.api_views.scan_use_cases.get_scan_details") as get_scan_details:
			get_scan_details.return_value = payload

			response = self.client.get(reverse("scan:scan_details", args=[7]))

		self.assertEqual(response.status_code, 200)
		self.assertJSONEqual(response.content, payload)
		get_scan_details.assert_called_once_with(scan_id=7)


class ScanApiIntegrationTests(TestCase):
	def test_scan_history_reads_real_repository_data(self):
		"""History endpoint order."""
		older_scan = ScanSession.objects.create(duration=4, device_count=1)
		newer_scan = ScanSession.objects.create(duration=9, device_count=2)

		response = self.client.get(reverse("scan:scan_history"))

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["status"], "success")
		self.assertEqual([scan["id"] for scan in payload["scans"]], [
			newer_scan.id,
			older_scan.id,
		])
		self.assertEqual(payload["scans"][0]["device_count"], 2)

	def test_scan_details_reads_real_repository_data(self):
		"""Details endpoint data."""
		session = ScanSession.objects.create(duration=5, device_count=2)
		Device.objects.create(
			scan_session=session,
			mac_address="BB:BB:BB:BB:BB:BB",
			rssi="-55",
			raw_data="face",
			company_name="BeaconCo",
			device_name="Beacon",
			decoded_data={"FF": {"data": "1234"}},
		)
		Device.objects.create(
			scan_session=session,
			mac_address="AA:AA:AA:AA:AA:AA",
			rssi="-40",
			raw_data="cafe",
			company_name=None,
			device_name="Alpha",
			decoded_data={"09": {"data": "416c706861"}},
		)

		response = self.client.get(reverse("scan:scan_details", args=[session.id]))

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["status"], "success")
		self.assertEqual(payload["scan"]["id"], session.id)
		self.assertEqual(payload["scan"]["device_count"], 2)
		self.assertEqual([device["mac"] for device in payload["scan"]["devices"]], [
			"AA:AA:AA:AA:AA:AA",
			"BB:BB:BB:BB:BB:BB",
		])
		self.assertEqual(payload["scan"]["devices"][0]["device_name"], "Alpha")
		self.assertEqual(payload["scan"]["devices"][1]["company_name"], "BeaconCo")

	def test_scan_details_returns_error_payload_for_unknown_scan(self):
		"""Details missing scan."""
		response = self.client.get(reverse("scan:scan_details", args=[999999]))

		self.assertEqual(response.status_code, 200)
		self.assertJSONEqual(
			response.content,
			{"status": "error", "message": "Scan not found."},
		)


class ScanUseCasesTests(SimpleTestCase):
	def test_start_scan_configures_scanner_persists_devices_and_returns_payload(self):
		"""Use case start success."""
		repository = MagicMock()
		repository.create_scan_session_with_devices.return_value = SimpleNamespace(id=42)
		devices = {
			"AA:BB": {
				"mac": "AA:BB",
				"rssi": -55,
				"data": "abcd",
			}
		}

		with patch("Scan.application.scan_use_cases.BluetoothScanner") as bluetooth_scanner:
			scanner = bluetooth_scanner.return_value
			scanner.scan.return_value = devices
			use_cases = ScanUseCases(repository=repository)

			result = use_cases.start_scan(duration=9, port="COM9")

		bluetooth_scanner.assert_called_once_with(port="COM9")
		scanner.configure_serial.assert_called_once_with()
		scanner.scan.assert_called_once_with(duration=9)
		scanner.close.assert_called_once_with()
		repository.create_scan_session_with_devices.assert_called_once_with(
			duration=9,
			devices=devices,
		)
		self.assertEqual(
			result,
			{
				"status": "success",
				"scan_id": 42,
				"device_count": 1,
				"devices": devices,
			},
		)

	def test_start_scan_closes_scanner_when_scan_fails(self):
		"""Use case closes scanner."""
		repository = MagicMock()

		with patch("Scan.application.scan_use_cases.BluetoothScanner") as bluetooth_scanner:
			scanner = bluetooth_scanner.return_value
			scanner.scan.side_effect = RuntimeError("scan failed")
			use_cases = ScanUseCases(repository=repository)

			with self.assertRaisesMessage(RuntimeError, "scan failed"):
				use_cases.start_scan(duration=3, port="COM3")

		scanner.configure_serial.assert_called_once_with()
		scanner.close.assert_called_once_with()
		repository.create_scan_session_with_devices.assert_not_called()

	def test_get_scan_history_wraps_repository_payload(self):
		"""Use case history response."""
		repository = MagicMock()
		repository.get_scan_history.return_value = [{"id": 1}]
		use_cases = ScanUseCases(repository=repository)

		result = use_cases.get_scan_history()

		self.assertEqual(result, {"status": "success", "scans": [{"id": 1}]})

	def test_get_scan_details_returns_error_for_missing_scan(self):
		"""Use case missing scan."""
		repository = MagicMock()
		repository.get_scan_details.return_value = None
		use_cases = ScanUseCases(repository=repository)

		result = use_cases.get_scan_details(scan_id=99)

		self.assertEqual(result, {"status": "error", "message": "Scan not found."})


class ScanRepositoryTests(SimpleTestCase):
	def test_create_scan_session_with_devices_creates_session_and_bulk_inserts_devices(self):
		"""Repository create mapping."""
		repository = ScanRepository()
		session = ScanSession(id=3, duration=6, device_count=1)
		devices = {
			"AA:BB": {
				"mac": "AA:BB",
				"rssi": -42,
				"data": "abcd",
				"company_name": "Acme",
				"device_name": "Sensor",
				"sep_data": {"09": {"data": "53656e736f72"}},
			}
		}

		with patch("Scan.data_access.scan_repository.ScanSession.objects.create", return_value=session) as create_session, patch(
			"Scan.data_access.scan_repository.Device.objects.bulk_create"
		) as bulk_create:
			result = repository.create_scan_session_with_devices.__wrapped__(
				repository,
				duration="6",
				devices=devices,
			)

		self.assertIs(result, session)
		create_session.assert_called_once_with(duration=6, device_count=1)
		inserted_devices = bulk_create.call_args.args[0]
		self.assertEqual(len(inserted_devices), 1)
		self.assertIsInstance(inserted_devices[0], Device)
		self.assertEqual(inserted_devices[0].scan_session, session)
		self.assertEqual(inserted_devices[0].mac_address, "AA:BB")
		self.assertEqual(inserted_devices[0].rssi, "-42")
		self.assertEqual(inserted_devices[0].raw_data, "abcd")
		self.assertEqual(inserted_devices[0].company_name, "Acme")
		self.assertEqual(inserted_devices[0].device_name, "Sensor")
		self.assertEqual(inserted_devices[0].decoded_data, {"09": {"data": "53656e736f72"}})

	def test_get_scan_history_serializes_latest_scans(self):
		"""Repository history summary."""
		repository = ScanRepository()
		scan = SimpleNamespace(
			id=5,
			timestamp=SimpleNamespace(isoformat=lambda: "2026-03-16T12:00:00+00:00"),
			duration=10,
			device_count=4,
		)
		manager = MagicMock()
		manager.order_by.return_value.__getitem__.return_value = [scan]

		with patch("Scan.data_access.scan_repository.ScanSession.objects.all", return_value=manager):
			result = repository.get_scan_history(limit=50)

		self.assertEqual(
			result,
			[
				{
					"id": 5,
					"timestamp": "2026-03-16T12:00:00+00:00",
					"duration": 10,
					"device_count": 4,
				}
			],
		)

	def test_get_scan_details_returns_none_when_scan_is_missing(self):
		"""Repository missing details."""
		repository = ScanRepository()
		queryset = MagicMock()
		queryset.prefetch_related.return_value.first.return_value = None

		with patch("Scan.data_access.scan_repository.ScanSession.objects.filter", return_value=queryset):
			result = repository.get_scan_details(scan_id=123)

		self.assertIsNone(result)

	def test_get_scan_details_serializes_devices(self):
		"""Repository details payload."""
		repository = ScanRepository()
		device = SimpleNamespace(
			id=8,
			mac_address="AA:BB",
			rssi="-61",
			raw_data="beef",
			company_name="Acme",
			device_name="Tag",
			decoded_data={"FF": {"data": "004c"}},
		)
		devices_manager = MagicMock()
		devices_manager.all.return_value.order_by.return_value = [device]
		scan = SimpleNamespace(
			id=6,
			timestamp=SimpleNamespace(isoformat=lambda: "2026-03-16T12:05:00+00:00"),
			duration=7,
			device_count=1,
			devices=devices_manager,
		)
		queryset = MagicMock()
		queryset.prefetch_related.return_value.first.return_value = scan

		with patch("Scan.data_access.scan_repository.ScanSession.objects.filter", return_value=queryset):
			result = repository.get_scan_details(scan_id=6)

		self.assertEqual(
			result,
			{
				"id": 6,
				"timestamp": "2026-03-16T12:05:00+00:00",
				"duration": 7,
				"device_count": 1,
				"devices": [
					{
						"id": 8,
						"mac": "AA:BB",
						"rssi": "-61",
						"data": "beef",
						"company_name": "Acme",
						"device_name": "Tag",
						"sep_data": {"FF": {"data": "004c"}},
					}
				],
			},
		)


class ScanRepositoryIntegrationTests(TestCase):
	def test_create_scan_session_with_devices_persists_models(self):
		"""Repository create persists."""
		repository = ScanRepository()
		devices = {
			"AA:BB:CC:DD:EE:FF": {
				"mac": "AA:BB:CC:DD:EE:FF",
				"rssi": -42,
				"data": "abcd",
				"company_name": "Acme",
				"device_name": "Sensor",
				"sep_data": {"09": {"data": "53656e736f72"}},
			},
			"11:22:33:44:55:66": {
				"mac": "11:22:33:44:55:66",
				"rssi": -60,
				"data": "beef",
				"company_name": None,
				"device_name": None,
				"sep_data": None,
			},
		}

		session = repository.create_scan_session_with_devices(duration="6", devices=devices)

		self.assertEqual(ScanSession.objects.count(), 1)
		self.assertEqual(Device.objects.count(), 2)
		session.refresh_from_db()
		self.assertEqual(session.duration, 6)
		self.assertEqual(session.device_count, 2)

		persisted_devices = list(session.devices.order_by("mac_address"))
		self.assertEqual(persisted_devices[0].mac_address, "11:22:33:44:55:66")
		self.assertEqual(persisted_devices[0].rssi, "-60")
		self.assertIsNone(persisted_devices[0].company_name)
		self.assertEqual(persisted_devices[1].mac_address, "AA:BB:CC:DD:EE:FF")
		self.assertEqual(persisted_devices[1].company_name, "Acme")
		self.assertEqual(persisted_devices[1].device_name, "Sensor")
		self.assertEqual(
			persisted_devices[1].decoded_data,
			{"09": {"data": "53656e736f72"}},
		)

	def test_get_scan_history_returns_latest_scans_from_database(self):
		"""Repository history database."""
		repository = ScanRepository()
		older_scan = ScanSession.objects.create(duration=4, device_count=1)
		newer_scan = ScanSession.objects.create(duration=9, device_count=3)

		result = repository.get_scan_history(limit=10)

		self.assertEqual(len(result), 2)
		self.assertEqual(result[0]["id"], newer_scan.id)
		self.assertEqual(result[0]["duration"], 9)
		self.assertEqual(result[0]["device_count"], 3)
		self.assertEqual(result[1]["id"], older_scan.id)

	def test_get_scan_details_returns_devices_from_database(self):
		"""Repository details database."""
		repository = ScanRepository()
		session = ScanSession.objects.create(duration=5, device_count=2)
		Device.objects.create(
			scan_session=session,
			mac_address="BB:BB:BB:BB:BB:BB",
			rssi="-55",
			raw_data="face",
			company_name="BeaconCo",
			device_name="Beacon",
			decoded_data={"FF": {"data": "1234"}},
		)
		Device.objects.create(
			scan_session=session,
			mac_address="AA:AA:AA:AA:AA:AA",
			rssi="-40",
			raw_data="cafe",
			company_name=None,
			device_name="Alpha",
			decoded_data={"09": {"data": "416c706861"}},
		)

		result = repository.get_scan_details(scan_id=session.id)

		self.assertEqual(result["id"], session.id)
		self.assertEqual(result["duration"], 5)
		self.assertEqual(result["device_count"], 2)
		self.assertEqual([device["mac"] for device in result["devices"]], [
			"AA:AA:AA:AA:AA:AA",
			"BB:BB:BB:BB:BB:BB",
		])
		self.assertEqual(result["devices"][0]["device_name"], "Alpha")
		self.assertEqual(result["devices"][1]["company_name"], "BeaconCo")

	def test_get_scan_details_returns_none_for_unknown_id(self):
		"""Repository unknown id."""
		repository = ScanRepository()

		self.assertIsNone(repository.get_scan_details(scan_id=999999))


class ScanServiceHourlyCounterTests(SimpleTestCase):
	def test_counter_emit_mode_defaults_to_hour(self):
		service = ScanService()

		self.assertEqual(service._counter_emit_mode, "hour")

	def test_counter_emit_mode_can_be_minute_via_env(self):
		with patch.dict("os.environ", {"HOURLY_COUNTER_BROADCAST_EVERY": "minute"}):
			service = ScanService()

		self.assertEqual(service._counter_emit_mode, "minute")
		self.assertEqual(service._counter_emit_delta(), timedelta(minutes=1))

	def test_roll_hour_if_needed_uses_minute_cadence_with_hour_keys(self):
		with patch.dict("os.environ", {"HOURLY_COUNTER_BROADCAST_EVERY": "minute"}):
			service = ScanService()

		start = datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc)
		service._current_hour_start = start
		service._hourly_unique_devices = {"AA"}

		with patch("Scan.application.background_scan_service.ws_server.broadcast_sync") as broadcast_sync:
			service._roll_hour_if_needed(now=start + timedelta(minutes=3, seconds=5))

		self.assertEqual(broadcast_sync.call_count, 3)
		first = broadcast_sync.call_args_list[0].args[0]
		second = broadcast_sync.call_args_list[1].args[0]
		third = broadcast_sync.call_args_list[2].args[0]
		self.assertEqual(first["type"], "hourly_unique_device_count")
		self.assertEqual(first["hour_start"], "2026-04-13T10:00:00+00:00")
		self.assertEqual(first["hour_end"], "2026-04-13T10:01:00+00:00")
		self.assertEqual(first["unique_device_count"], 1)
		self.assertEqual(second["hour_start"], "2026-04-13T10:01:00+00:00")
		self.assertEqual(second["unique_device_count"], 0)
		self.assertEqual(third["hour_start"], "2026-04-13T10:02:00+00:00")
		self.assertEqual(third["unique_device_count"], 0)
		self.assertEqual(service._current_hour_start, start + timedelta(minutes=3))

	def test_track_hourly_devices_counts_unique_mac_addresses_case_insensitive(self):
		service = ScanService()

		service._track_hourly_devices(
			{
				"1": {"mac": "aa:bb:cc:dd:ee:ff"},
				"2": {"mac": "AA:BB:CC:DD:EE:FF"},
				"3": {"mac": None},
				"4": {},
			}
		)

		self.assertEqual(service._hourly_unique_devices, {"AA:BB:CC:DD:EE:FF"})
		self.assertEqual(service._hourly_company_unique_devices, {"Unknown": {"AA:BB:CC:DD:EE:FF"}})

	def test_track_hourly_devices_tracks_unique_devices_per_company(self):
		service = ScanService()

		service._track_hourly_devices(
			{
				"1": {"mac": "AA:BB", "company_name": "Laird"},
				"2": {"mac": "AA:BB", "company_name": "Laird"},
				"3": {"mac": "CC:DD", "company_name": "Laird"},
				"4": {"mac": "EE:FF", "company_name": "Nordic"},
			}
		)

		self.assertEqual(service._hourly_company_unique_devices["Laird"], {"AA:BB", "CC:DD"})
		self.assertEqual(service._hourly_company_unique_devices["Nordic"], {"EE:FF"})

	def test_roll_hour_if_needed_broadcasts_completed_hour_and_resets_counter(self):
		service = ScanService()
		start_hour = datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc)
		service._current_hour_start = start_hour
		service._hourly_unique_devices = {"AA", "BB"}
		service._hourly_company_unique_devices = {"Laird": {"AA", "BB"}}

		with patch("Scan.application.background_scan_service.ws_server.broadcast_sync") as broadcast_sync:
			service._roll_hour_if_needed(now=start_hour + timedelta(hours=1, seconds=1))

		self.assertEqual(broadcast_sync.call_count, 1)
		payload = broadcast_sync.call_args.args[0]
		self.assertEqual(payload["type"], "hourly_unique_device_count")
		self.assertEqual(payload["hour_start"], "2026-04-13T10:00:00+00:00")
		self.assertEqual(payload["hour_end"], "2026-04-13T11:00:00+00:00")
		self.assertEqual(payload["unique_device_count"], 2)
		self.assertEqual(payload["company_device_counts"], {"Laird": 2})
		self.assertEqual(service._current_hour_start, start_hour + timedelta(hours=1))
		self.assertEqual(service._hourly_unique_devices, set())
		self.assertEqual(service._hourly_company_unique_devices, {})

	def test_roll_hour_if_needed_broadcasts_each_elapsed_hour(self):
		service = ScanService()
		start_hour = datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc)
		service._current_hour_start = start_hour
		service._hourly_unique_devices = {"AA"}

		with patch("Scan.application.background_scan_service.ws_server.broadcast_sync") as broadcast_sync:
			service._roll_hour_if_needed(now=start_hour + timedelta(hours=3, minutes=5))

		self.assertEqual(broadcast_sync.call_count, 3)
		first = broadcast_sync.call_args_list[0].args[0]
		second = broadcast_sync.call_args_list[1].args[0]
		third = broadcast_sync.call_args_list[2].args[0]
		self.assertEqual(first["hour_start"], "2026-04-13T10:00:00+00:00")
		self.assertEqual(first["unique_device_count"], 1)
		self.assertEqual(second["hour_start"], "2026-04-13T11:00:00+00:00")
		self.assertEqual(second["unique_device_count"], 0)
		self.assertEqual(third["hour_start"], "2026-04-13T12:00:00+00:00")
		self.assertEqual(third["unique_device_count"], 0)
		self.assertEqual(service._current_hour_start, start_hour + timedelta(hours=3))
