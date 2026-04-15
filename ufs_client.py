from __future__ import annotations

import requests

from config import UFS_FORECAST_ENDPOINT, UFS_TIMEOUT_SECONDS


def call_ufs_forecast(input_payload: dict) -> dict:
    """
    Send one node-port-KPI message payload to the UFS endpoint and return result JSON.
    """
    response = requests.post(
        UFS_FORECAST_ENDPOINT,
        json=input_payload,
        timeout=UFS_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()
