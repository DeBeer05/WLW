from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from Scan.application.scan_use_cases import ScanUseCases
from Scan.data_access.scan_repository import ScanRepository
from Scan.models import Device, ScanSession


class ScanApiViewTests(SimpleTestCase):
	def test_index_returns_status_payload(self):
		"""Index returns the API status payload."""
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
		"""Start scan passes JSON duration and port to the use case."""
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
		"""Start scan falls back to default duration and port when the body is empty."""
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
		"""Start scan returns an error payload when the use case raises an exception."""
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
		"""Scan history returns the JSON payload from the use case."""
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
		"""Scan details forwards the route scan id to the use case."""
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
		"""Scan history endpoint returns persisted scans in newest-first order."""
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
		"""Scan details endpoint returns persisted devices ordered by MAC address."""
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
		"""Scan details endpoint returns an error payload for an unknown scan id."""
		response = self.client.get(reverse("scan:scan_details", args=[999999]))

		self.assertEqual(response.status_code, 200)
		self.assertJSONEqual(
			response.content,
			{"status": "error", "message": "Scan not found."},
		)


class ScanUseCasesTests(SimpleTestCase):
	def test_start_scan_configures_scanner_persists_devices_and_returns_payload(self):
		"""Start scan configures the scanner, persists results, and returns a success payload."""
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
		"""Start scan always closes the scanner when the scan operation fails."""
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
		"""Get scan history wraps repository results in a success response."""
		repository = MagicMock()
		repository.get_scan_history.return_value = [{"id": 1}]
		use_cases = ScanUseCases(repository=repository)

		result = use_cases.get_scan_history()

		self.assertEqual(result, {"status": "success", "scans": [{"id": 1}]})

	def test_get_scan_details_returns_error_for_missing_scan(self):
		"""Get scan details returns an error response when the scan does not exist."""
		repository = MagicMock()
		repository.get_scan_details.return_value = None
		use_cases = ScanUseCases(repository=repository)

		result = use_cases.get_scan_details(scan_id=99)

		self.assertEqual(result, {"status": "error", "message": "Scan not found."})


class ScanRepositoryTests(SimpleTestCase):
	def test_create_scan_session_with_devices_creates_session_and_bulk_inserts_devices(self):
		"""Repository create maps input devices into bulk-created Device rows."""
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
		"""Repository get_scan_history serializes the latest scan summaries."""
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
		"""Repository get_scan_details returns None when the scan is missing."""
		repository = ScanRepository()
		queryset = MagicMock()
		queryset.prefetch_related.return_value.first.return_value = None

		with patch("Scan.data_access.scan_repository.ScanSession.objects.filter", return_value=queryset):
			result = repository.get_scan_details(scan_id=123)

		self.assertIsNone(result)

	def test_get_scan_details_serializes_devices(self):
		"""Repository get_scan_details serializes a scan and its devices."""
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
		"""Repository create persists a scan session and all associated devices."""
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
		"""Repository get_scan_history reads newest-first scans from the database."""
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
		"""Repository get_scan_details returns persisted device details from the database."""
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
		"""Repository get_scan_details returns None for an unknown database id."""
		repository = ScanRepository()

		self.assertIsNone(repository.get_scan_details(scan_id=999999))
