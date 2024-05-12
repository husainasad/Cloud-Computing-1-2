#!/bin/bash
sudo -u ubuntu -i <<'EOF'
sudo apt-get update -y
sudo apt install python3.10-venv -y
python3 -m venv projectenv
source projectenv/bin/activate
git clone -q https://github.com/husainasad/FaceFlow-Distributed.git
pip install --upgrade pip
pip install --upgrade setuptools
pip install aioboto3
pip install "fastapi[all]"
pip install pandas python-multipart

echo "[Unit]
Description=My Web server
After=multi-user.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/home/ubuntu/projectenv/bin/python -m uvicorn web_tier:app --host 0.0.0.0 --port 8000
WorkingDirectory=/home/ubuntu/FaceFlow-Distributed
User=ubuntu
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/web-server.service

sudo chmod 644 /etc/systemd/system/web-server.service
sudo systemctl start web-server
sudo systemctl enable web-server
EOF