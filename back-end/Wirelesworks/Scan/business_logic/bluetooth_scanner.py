import os
import time

import serial
import yaml

from Scan.utils.loading import Loading


class BluetoothScanner:
    """Core BLE scanner business logic independent from Django views."""

    def __init__(self, port="/dev/ttyS2", baudrate=115200, timeout=0.2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.unique_devices = {}
        self.serial_bus = None

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.company_identifiers = self._load_company_dict(
            os.path.join(base_dir, "yaml_files", "company_identifiers.yaml")
        )
        self.ad_types = self._load_type_dict(
            os.path.join(base_dir, "yaml_files", "ad_types.yaml")
        )
        self.loading_bar = Loading("Scanning")

    def _load_company_dict(self, file_path):
        yaml_dict = {}
        with open(file_path, "r", encoding="utf-8") as file:
            yaml_contents = yaml.load(file, Loader=yaml.BaseLoader)
        for company in yaml_contents["company_identifiers"]:
            yaml_dict[company["value"]] = company["name"]
        return yaml_dict

    def _load_type_dict(self, file_path):
        yaml_dict = {}
        with open(file_path, "r", encoding="utf-8") as file:
            yaml_contents = yaml.safe_load(file)
        for item in yaml_contents["ad_types"]:
            yaml_dict[str(item["value"]).zfill(2)] = item["name"]
        return yaml_dict

    def configure_serial(self):
        self.serial_bus = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        if self.serial_bus.is_open:
            self.serial_bus.close()
        self.serial_bus.open()
        self.serial_bus.send_break(0.1)
        time.sleep(3)
        self.serial_bus.write("AT+SFMT 1\r".encode())
        time.sleep(3)
        self.serial_bus.flushInput()
        self.serial_bus.flushOutput()
        time.sleep(3)

    def scan(self, duration=5):
        self.serial_bus.flushInput()
        ignore_list = ["", "\n"]

        command = f"AT+LSCN {duration}\r".encode()
        self.serial_bus.write(command)

        self.loading_bar.start_loading()
        ok_reached = False

        while not ok_reached:
            device = {}
            incoming_adv = self.serial_bus.readline().decode()

            if len(incoming_adv) > 28:
                device["mac"] = incoming_adv[6:20]
                device["rssi"] = incoming_adv[21:24]
                device["data"] = incoming_adv[26:-2]

                if device["data"] and device["data"][-1] == '"':
                    device["data"] = incoming_adv[26:-3]

                self.unique_devices[device["mac"]] = device
                self._decode_advert(self.unique_devices[device["mac"]])
            elif incoming_adv not in ignore_list:
                ok_reached = True

        self.loading_bar.stop_loading()
        time.sleep(0.1)
        return self.unique_devices

    def _decode_advert(self, device):
        offset = 2
        data = device.get("data")

        if data:
            device["sep_data"] = {}
            while offset < len(data):
                data_len = int(data[offset - 2 : offset], 16) * 2
                data_type = data[offset : offset + 2]
                data_data = data[offset + 2 : offset + data_len]

                device["sep_data"][data_type] = {
                    "data_len": data_len,
                    "data_type": data_type,
                    "data_type_str": self.ad_types.get(data_type),
                    "data": data_data,
                }

                if data_type == "FF":
                    self._get_company_name(device, data_data)
                elif data_type in ["08", "09"]:
                    self._get_device_name(device, data_data)

                offset += data_len + 2

    def _get_company_name(self, device, company_id):
        byte1 = company_id[:2]
        byte2 = company_id[2:4]
        company_id_rotated = byte2 + byte1
        comp_name = self.company_identifiers.get(str(company_id_rotated))
        if comp_name and comp_name not in ["Unknown", "N/A", "No Name Found"]:
            device["company_name"] = comp_name
        else:
            device["company_name"] = None

    def _get_device_name(self, device, hex_name):
        name = bytes.fromhex(hex_name.replace("\0", "")).decode()
        device["device_name"] = name

        if "PNL" in name.upper():
            device["company_name"] = "PNL"
        if "LAIRD" in name.upper():
            device["company_name"] = "Laird"

    def close(self):
        if self.serial_bus and self.serial_bus.is_open:
            self.serial_bus.close()
