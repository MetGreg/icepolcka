"""High impact weather statistics

This script calculates statistics for high impact weather situations. This includes hail/graupel and
heavy rain events.

The statistics include frequency, and area of the events. They are calculated for model and radar
observation alike. A hydrometeor classification is applied onto the radar data to retrieve
hydrometeor classes used to find high impact situations.

"""
import os
import sys

from icepolcka_utils import hiw, utils

STATS_CLASSES = {"Dolan": hiw.DolanStats, "wrf": hiw.WRFStats}
CONFIG_FILE = "job_config.yaml"


def _main(cfg_file, src, method, mp_id, hgt):
    cfg = utils.get_cfg(cfg_file)
    cfg['mp'] = mp_id
    cfg['source'] = src
    stats_obj = STATS_CLASSES[method](cfg, height=hgt)
    if os.path.exists(stats_obj.file_path):
        print("Datafile exists already")
        print("Exiting")
        sys.exit()
    stats_obj.get_stats()


if __name__ == "__main__":
    source = sys.argv[1]
    method_name = sys.argv[2]
    mp_scheme = sys.argv[3]
    height_idx = sys.argv[4]
    _main(CONFIG_FILE, source, method_name, mp_scheme, height_idx)
