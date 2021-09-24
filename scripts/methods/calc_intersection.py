"""Save intersection of Poldirad and Mira-35 as matrix

For all combinations of azimuth angles, this script calculates the great
circle distance (along the surface) at which beams of Mira-35 and Poldirad
would intersect. This distance is saved to a numpy matrix, where the outer
dimension is iterating over the Poldirad azimuth angles and the inner
dimensions is iteration over Mira-35 azimuth angles. For each combination,
a tuple of (Poldirad distance, Mira-35 distance) is saved that corresponds to
the point of intersection. The distance refers to the distance to the radar
in [m].

"""
import numpy as np

from icepolcka_utils.geo import get_target_distance, get_pos_from_dist
from icepolcka_utils.utils import load_config


def main():
    cfg = load_config()
    mira_site, poldi_site = cfg['sites']['Mira35'], cfg['sites']['Poldirad']
    matrix, dr, i = [], 10, 0

    for poldi_az in np.arange(0, 141, 1):
        matrix.append([])
        print("Poldi az: ", str(poldi_az))
        for mira_az in np.arange(0, 360, 1):
            min_mira, min_poldi = None, None
            min_d = dr
            for poldi_r in np.arange(0, 48000, dr):
                for mira_r in np.arange(0, 24000, dr):
                    poldi_pos = get_pos_from_dist(poldi_site, poldi_r, poldi_az)
                    mira_pos = get_pos_from_dist(mira_site, mira_r, mira_az)
                    d = get_target_distance(poldi_pos, mira_pos)
                    if d < min_d:
                        min_d = d
                        min_mira = mira_r
                        min_poldi = poldi_r
            matrix[i].append((min_poldi, min_mira))
        i += 1
    np.save(cfg['matrix']['Intersection'], np.array(matrix))


if __name__ == "__main__":
    main()
