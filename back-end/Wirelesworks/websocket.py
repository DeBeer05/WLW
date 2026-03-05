import asyncio
import websockets
import serial
import time

SERIAL_BUS = serial.Serial(
    port='/dev/ttyS2',
    baudrate=115200,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=1
)

CUSTOMERS = {
    "Ant-Tail": "0572",
    "Elpro": "0982",
    "Sensitech": "FD16",
    "Unisto": "2D45",
    "Nordic": "0059",
    "PostNL": "PNL"
}

clients = set()

def delay(n):
    time.sleep(n)

def serial_reset():
    SERIAL_BUS.reset_input_buffer()
    time.sleep(0.1)
    SERIAL_BUS.reset_output_buffer()
    time.sleep(0.1)

async def broadcast(message):
    if clients:
        await asyncio.wait([client.send(message) for client in clients])

async def scan_loop():
    while True:
        for customer in CUSTOMERS:
            await scan_customer(customer, CUSTOMERS[customer])
            await asyncio.sleep(0.5)

        await scan_general()
        await asyncio.sleep(0.5)

async def scan_customer(customer_name, customer_id):
    serial_reset()

    if customer_name == "PostNL":
        SCAN = f'AT+LSCN 5,"{customer_id}"\r'
    else:
        SCAN = 'AT+LSCN 4,"\{}\{}"\r'.format(customer_id[2:], customer_id[:2])

    SERIAL_BUS.write(SCAN.encode())
    await asyncio.sleep(5.5)

    adverts = SERIAL_BUS.read(4096)
    advert_list = set(adverts.split(b'\n'))

    for advert in advert_list:
        filtered_adv = advert[6:20] + b' ' + advert[25:-1]
        if len(filtered_adv) >= 14:
            message = f'{customer_name} | {filtered_adv.decode()}'
            await broadcast(message)

async def scan_general():
    serial_reset()
    SERIAL_BUS.write('AT+LSCN 3\r'.encode())
    await asyncio.sleep(3.5)

    adverts = SERIAL_BUS.read(4096)
    advert_list = set(adverts.split(b'\n'))

    for advert in advert_list:
        filtered_adv = advert[6:20] + b' ' + advert[25:-1]
        message = f'General | {filtered_adv.decode()}'
        await broadcast(message)

async def handler(websocket):
    clients.add(websocket)
    print("Client verbonden")
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)
        print("Client verbroken")

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket scanner draait op poort 8765")
        await scan_loop()

asyncio.run(main())