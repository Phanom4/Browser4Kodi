#!/usr/bin/env python3

import hashlib
import socket
import sqlite3
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


CONFIG = (
    Path.home()
    / ".kodi/userdata/addon_data/pvr.hts/instance-settings-1.xml"
)

DATABASE_DIR = (
    Path.home()
    / ".kodi/userdata/Database"
)

HBBTV_DB_VERSION = 1

HBBTV_DB = (
    DATABASE_DIR
    / f"HbbTV{HBBTV_DB_VERSION}.db"
)


def find_tv_database():
    databases = []

    for path in DATABASE_DIR.glob("TV*.db"):
        version = path.stem[2:]

        if version.isdigit():
            databases.append(
                (int(version), path)
            )

    if not databases:
        raise RuntimeError(
            f"Keine Kodi-TV-Datenbank in {DATABASE_DIR} gefunden"
        )

    return max(databases)[1]


TV_DB = find_tv_database()



HMF_MAP = 1
HMF_S64 = 2
HMF_STR = 3
HMF_BIN = 4
HMF_LIST = 5


def kodi_to_htsp_id(kodi_id):
    value = kodi_id & 0xffffffff
    return int.from_bytes(value.to_bytes(4, "little"), "big")


def load_kodi_ids():
    con = sqlite3.connect(f"file:{TV_DB}?mode=ro", uri=True)

    try:
        rows = con.execute(
            """
            SELECT iUniqueId
            FROM channels
            WHERE bIsRadio = 0
            """
        )

        return {
            kodi_to_htsp_id(row[0]): row[0]
            for row in rows
        }
    finally:
        con.close()


def load_settings():
    root = ET.parse(CONFIG).getroot()

    return {
        node.get("id"): node.text or ""
        for node in root.findall("setting")
        if node.get("id")
    }


def recv_exact(sock, size):
    data = bytearray()

    while len(data) < size:
        part = sock.recv(size - len(data))

        if not part:
            raise EOFError

        data.extend(part)

    return bytes(data)


def decode_int(data):
    value = 0

    for byte in data:
        value = (value << 8) | byte

    if data and data[0] & 0x80:
        value -= 1 << (8 * len(data))

    return value


def decode_field(field_type, data):
    if field_type == HMF_MAP:
        return decode_map(data)

    if field_type == HMF_LIST:
        return decode_list(data)

    if field_type == HMF_S64:
        return decode_int(data)

    if field_type == HMF_STR:
        return data.decode("utf-8", errors="replace")

    if field_type == HMF_BIN:
        return data

    return data


def decode_map(data):
    result = {}
    pos = 0

    while pos < len(data):
        field_type = data[pos]
        name_len = data[pos + 1]
        data_len = int.from_bytes(data[pos + 2:pos + 6], "big")
        pos += 6

        name = data[pos:pos + name_len].decode(
            "utf-8",
            errors="replace"
        )
        pos += name_len

        field_data = data[pos:pos + data_len]
        pos += data_len

        result[name] = decode_field(field_type, field_data)

    return result


def decode_list(data):
    result = []
    pos = 0

    while pos < len(data):
        field_type = data[pos]
        name_len = data[pos + 1]
        data_len = int.from_bytes(data[pos + 2:pos + 6], "big")
        pos += 6

        pos += name_len

        field_data = data[pos:pos + data_len]
        pos += data_len

        result.append(decode_field(field_type, field_data))

    return result


def encode_int(value):
    if value == 0:
        return b"\x00"

    size = max(1, (value.bit_length() + 7) // 8)
    return value.to_bytes(size, "big")


def encode_field(name, value):
    name = name.encode("utf-8")

    if isinstance(value, str):
        field_type = HMF_STR
        data = value.encode("utf-8")

    elif isinstance(value, int):
        field_type = HMF_S64
        data = encode_int(value)

    elif isinstance(value, bytes):
        field_type = HMF_BIN
        data = value

    else:
        raise TypeError

    return (
        bytes([field_type, len(name)])
        + len(data).to_bytes(4, "big")
        + name
        + data
    )

def send_message(sock, message):
    payload = b"".join(
        encode_field(name, value)
        for name, value in message.items()
    )

    sock.sendall(
        len(payload).to_bytes(4, "big") + payload
    )


def recv_message(sock):
    size = int.from_bytes(recv_exact(sock, 4), "big")
    return decode_map(recv_exact(sock, size))


def find_hbbtv_entries(obj):
    """
    Liefert die HbbTV-Einträge vollständig zurück.
    Es werden keine Felder herausgefiltert.
    """
    entries = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "hbbtv":
                if isinstance(value, list):
                    entries.extend(value)
                else:
                    entries.append(value)
            else:
                entries.extend(find_hbbtv_entries(value))

    elif isinstance(obj, list):
        for value in obj:
            entries.extend(find_hbbtv_entries(value))

    return entries

def get_hbbtv_name(entry):
    title = entry.get("title", [])

    if not isinstance(title, list):
        return ""

    for item in title:
        if isinstance(item, dict):
            name = item.get("name")

            if name:
                return name

    return ""


def create_database():
    con = sqlite3.connect(HBBTV_DB)

    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS hbbtv_apps (
                id INTEGER PRIMARY KEY,
                iUniqueId INTEGER NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL
            )
            """
        )

        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_hbbtv_apps_iUniqueId
            ON hbbtv_apps(iUniqueId)
            """
        )

        con.execute("DELETE FROM hbbtv_apps")
        con.commit()

    finally:
        con.close()


def main():
    kodi_ids = load_kodi_ids()
    settings = load_settings()

    host = settings.get("host", "127.0.0.1")
    port = int(settings.get("htsp_port", "9982"))
    username = settings.get("user", "")
    password = settings.get("pass", "")

    create_database()

    con = sqlite3.connect(HBBTV_DB)

    try:
        with socket.create_connection((host, port), timeout=10) as sock:

            send_message(sock, {
                "method": "hello",
                "clientname": "HbbTV URL Reader",
                "htspversion": 35,
            })

            hello = recv_message(sock)
            challenge = hello["challenge"]

            digest = hashlib.sha1(
                password.encode("utf-8") + challenge
            ).digest()

            send_message(sock, {
                "method": "authenticate",
                "username": username,
                "digest": digest,
            })

            recv_message(sock)

            send_message(sock, {
                "method": "enableAsyncMetadata",
                "epg": 0,
            })

            while True:
                msg = recv_message(sock)

                if msg.get("method") == "channelAdd":
                    htsp_id = msg.get("channelId")
                    kodi_id = kodi_ids.get(htsp_id)

                    if kodi_id is None:
                        continue

                    entries = find_hbbtv_entries(msg)

                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue

                        for apps in entry.values():
                            if not isinstance(apps, list):
                                continue

                            for app in apps:
                                if not isinstance(app, dict):
                                    continue

                                name = get_hbbtv_name(app)
                                url = app.get("url", "")

                                if not name or not url:
                                    continue

                                con.execute(
                                    """
                                    INSERT INTO hbbtv_apps (
                                        iUniqueId,
                                        name,
                                        url
                                    )
                                    VALUES (?, ?, ?)
                                    """,
                                    (
                                        kodi_id,
                                        name,
                                        url,
                                    ),
                                )

                elif msg.get("method") == "initialSyncCompleted":
                    break

        con.commit()

    finally:
        con.close()

if __name__ == "__main__":
    main()
