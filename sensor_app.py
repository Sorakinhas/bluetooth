import asyncio
from datetime import datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop

CHARACTERISTIC_UUID = "0000ffe8-0000-1000-8000-00805f9b34fb"
ACTIVATION_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"
SENSOR_MAC = "D9:64:55:A5:39:17"
LOG_FILE = Path.home() / "Documentos" / "sensor_log.csv"


class SensorApp(QMainWindow):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop
        self.setWindowTitle("LT_3917 - Monitor de Temperatura/Umidade")

        self.label_status = QLabel("Status: aguardando conexão...")
        self.label_dados = QLabel("Temperatura: -- °C\nUmidade: -- %")
        self.console = QTextEdit()
        self.console.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.label_status)
        layout.addWidget(self.label_dados)
        layout.addWidget(self.console)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.loop.create_task(self.run_ble_loop())

    async def run_ble_loop(self):
        while True:
            try:
                await self.scan_and_connect()
            except Exception as exc:  # noqa: BLE001
                self.label_status.setText(f"Erro: {exc}")
                self.console.append(f"[erro] {exc}")
            self.label_status.setText("Desconectado. Retentando em 5s...")
            await asyncio.sleep(5)

    async def scan_and_connect(self):
        self.label_status.setText("Escaneando dispositivos BLE...")
        self.console.append("[scan] Iniciando busca por dispositivos BLE...")

        devices = await BleakScanner.discover(timeout=10.0)
        for d in devices:
            self.console.append(
                f"Dispositivo encontrado: {d.name or 'Sem Nome'} - {d.address}"
            )

        target = next(
            (
                d
                for d in devices
                if "LT_3917" in (d.name or "") or d.address == SENSOR_MAC
            ),
            None,
        )
        if not target:
            self.console.append(
                "Nenhum dispositivo compatível encontrado. Retentando em 5s..."
            )
            await asyncio.sleep(5)
            return

        self.label_status.setText(
            f"Conectando a {target.name or 'Sem nome'} ({target.address})..."
        )
        self.console.append(f"Conectando a {target.address}...")

        async with BleakClient(
            target.address, disconnected_callback=self.on_disconnect
        ) as client:
            if not client.is_connected:
                self.console.append("Falha na conexão com o dispositivo BLE.")
                return

            self.label_status.setText("Conectado! Ativando sensor...")

            try:
                await client.write_gatt_char(ACTIVATION_UUID, b"\x01", response=False)
                self.console.append("[cmd] Comando de ativação (FFE9) enviado.")
            except Exception as exc:  # noqa: BLE001
                self.console.append(f"[erro] Falha ao ativar notificações: {exc}")

            await client.start_notify(CHARACTERISTIC_UUID, self.notification_handler)
            self.console.append("Notificações iniciadas (FFE8). Aguardando dados...")

            while client.is_connected:
                await asyncio.sleep(1)

    def on_disconnect(self, client: BleakClient):  # noqa: D401
        """Callback disparado em desconexão."""
        self.console.append("[info] Dispositivo desconectado.")

    def notification_handler(self, _: int, data: bytearray):
        decoded = self.decode_data(data)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.label_dados.setText(
            f"Temperatura: {decoded['temperatura']} °C\nUmidade: {decoded['umidade']} %"
        )
        self.console.append(
            f"[{timestamp}] RAW: {decoded['raw_hex']} → T: {decoded['temperatura']} | U: {decoded['umidade']}"
        )
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(
                f"{timestamp},{decoded['raw_hex']},{decoded['temperatura']},{decoded['umidade']}\n"
            )

    @staticmethod
    def decode_data(data: bytes):
        hex_str = data.hex()
        try:
            temp_raw = int.from_bytes(data[6:8], byteorder="little") / 100
            humi_raw = int.from_bytes(data[8:10], byteorder="little") / 100
        except Exception:  # noqa: BLE001
            temp_raw, humi_raw = None, None
        return {"raw_hex": hex_str, "temperatura": temp_raw, "umidade": humi_raw}


def main():
    app = QApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = SensorApp(loop)
    window.resize(500, 300)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
