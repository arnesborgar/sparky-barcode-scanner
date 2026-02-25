# Pi Barcode Scanner for SparkyFitness

Scan barcodes from a USB scanner, look up nutrition data, and log food entries to SparkyFitness — all hands-free.

## How It Works

```
USB Scanner → barcode_scanner_v2.py → SparkyFitness API → Food Diary
```

**Nutrition lookup pipeline (3-tier fallback):**
1. **OpenFoodFacts `nutriments`** — declared label values
2. **OpenFoodFacts `nutriments_estimated`** — computed from ingredients
3. **USDA FoodData Central** — searched by barcode → brand+name → name

If all sources return zero macros, the food is logged with `[REVIEW]` in the name and `needs_review: true` in `custom_nutrients` for manual correction.

**Meal type** is auto-detected by time of day (configurable windows). ALL CAPS names/brands are normalized to Title Case.

## Requirements

- Raspberry Pi (tested on Bookworm, Python 3.11)
- USB barcode scanner (HID keyboard device)
- SparkyFitness server with an API key that has `diary` permission

## Setup

```bash
# Create working directory
mkdir -p ~/barcode-scanner && cd ~/barcode-scanner

# Create virtual environment (required on Bookworm)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env   # Set SPARKY_URL and SPARKY_API_KEY at minimum
```

## Configuration (.env)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SPARKY_URL` | Yes | `http://localhost:3010` | SparkyFitness server URL |
| `SPARKY_API_KEY` | Yes | — | API key with `diary` permission |
| `BREAKFAST_WINDOW` | No | `05:00-10:00` | HH:MM-HH:MM range |
| `LUNCH_WINDOW` | No | `11:00-13:00` | HH:MM-HH:MM range |
| `DINNER_WINDOW` | No | `14:00-16:00` | HH:MM-HH:MM range |
| `USDA_PROVIDER_ID` | No | — | Provider ID from Settings → Integrations |
| `SCALE_URL` | No | — | ESPHome scale REST endpoint (e.g. `http://10.1.1.x/sensor/weight`) |
| `SCANNER_DEVICE` | No | auto-detect | evdev path (e.g. `/dev/input/event0`) |

Scans outside all meal windows default to **Snack**.

## Running Manually

```bash
# With USB scanner (needs root for evdev)
sudo /home/pi/barcode-scanner/.venv/bin/python3 barcode_scanner_v2.py

# Without scanner (type barcodes manually — for testing)
python3 barcode_scanner_v2.py
```

## systemd Service (Auto-Start on Boot)

Create `/etc/systemd/system/barcode-scanner.service`:

```ini
[Unit]
Description=SparkyFitness Barcode Scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/barcode-scanner
EnvironmentFile=/home/pi/barcode-scanner/.env
ExecStart=/home/pi/barcode-scanner/.venv/bin/python3 /home/pi/barcode-scanner/barcode_scanner_v2.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable barcode-scanner
sudo systemctl start barcode-scanner
```

## Operations

```bash
# View live logs
journalctl -u barcode-scanner -f

# View recent logs
journalctl -u barcode-scanner --since "1 hour ago"

# Restart after updating the script
sudo systemctl restart barcode-scanner

# Stop the service
sudo systemctl stop barcode-scanner

# Check status
sudo systemctl status barcode-scanner
```

## Updating the Script

From your development machine:
```bash
scp barcode_scanner_v2.py pi@<pi-ip>:~/barcode-scanner/
ssh pi@<pi-ip> sudo systemctl restart barcode-scanner
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `SPARKY_API_KEY is not set` | Add key to `.env` — generate in SparkyFitness → Settings → API Keys |
| `PermissionError` on `/dev/input/eventN` | Run as root or via the systemd service |
| `Device busy` | Another instance is grabbing the device — `sudo pkill -f barcode_scanner` |
| Scanner not detected | Run `python3 -m evdev.evtest` to find the correct event path, set `SCANNER_DEVICE` in `.env` |
| `[REVIEW]` in food name | Nutrition data was incomplete from all sources — edit the food in SparkyFitness UI |
| `fetch failed` / 500 from OFF | Transient — SparkyFitness server couldn't reach OpenFoodFacts. Rescan in a few seconds |
| Wrong meal type | Adjust `BREAKFAST_WINDOW` / `LUNCH_WINDOW` / `DINNER_WINDOW` in `.env` |

## Files

| File | Purpose |
|---|---|
| `barcode_scanner_v2.py` | Main scanner script (production) |
| `barcode_scanner.py` | Legacy v1 (do not use — relies on deprecated server endpoint) |
| `.env.example` | Configuration template |
| `requirements.txt` | Python dependencies (`requests`, `evdev`) |
| `barcode-scanner.service` | systemd unit file |
