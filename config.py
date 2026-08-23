"""Central configuration for the Mobile Century TSE project."""

from pathlib import Path

# Root of the extracted dataset on this machine.
DATA_ROOT = Path(r"D:\Transportation\Data\MobileCentury_data_final_ver3")

GPS_LOGS = DATA_ROOT / "GPS_logs"
NB_TRIPS = DATA_ROOT / "NB_veh_files"
SB_TRIPS = DATA_ROOT / "SB_veh_files"
