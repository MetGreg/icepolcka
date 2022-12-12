"""Microphysical schemes

This module contains a class for each of the microphysical schemes used in my analyses. These
classes provide some functionality such as calculating particle size distributions.

"""
import math
import numpy as np


class MP8:
    """Thompson 2-moment scheme

    Corresponding publication: https://doi.org/10.1175/2008MWR2387.1

    """
    def __init__(self):
        self.rho_h = {'rain': 1000}
        self.mass_a = {'rain': np.pi/6*self.rho_h['rain']}
        self.mass_b = {'rain': 3}
        self.mu_param = {'rain': 0}

    def get_psd(self, hm_name, diam, q_mass, q_number):
        """Calculate PSD

        Calculates particle size distributions that are in the form of a gamma distribution.

        Args:
            hm_name (str): Name of hydrometeor class.
            diam (float): Particle diameter for which the number concentration will be returned.
            q_mass (float or ~numpy.ndarray): Mass mixing ratio.
            q_number (float or ~numpy.ndarray): Number concentration mixing ratio.

        Returns:
            float or ~numpy.ndarray:
                Number of particles of the given particle diameter (Particles/(kg*m).

        """
        assert hm_name == "rain", "Only rain PSD possible at the moment"
        lam = self._get_slope(hm_name, q_mass, q_number)
        n_0 = self._get_intercept(hm_name, q_mass, q_number)
        psd = n_0 * diam**self.mu_param[hm_name] * np.exp(-lam * diam)
        return psd

    def _get_slope(self, hm_name, q_mass, q_number):
        cre2 = self.mu_param[hm_name] + 1
        cre3 = self.mass_b[hm_name] + self.mu_param[hm_name] + 1
        crg2 = math.gamma(cre2)
        crg3 = math.gamma(cre3)
        lam = ((self.mass_a[hm_name]*crg3/crg2)*q_number/q_mass)**(1/3)
        return lam

    def _get_intercept(self, hm_name, q_mass, q_number):
        lam = self._get_slope(hm_name, q_mass, q_number)
        cre2 = self.mu_param[hm_name] + 1
        crg2 = math.gamma(cre2)
        n_0 = q_number * 1/crg2 * lam**cre2
        return n_0


class MP10:
    """Morrison 2-moment scheme

    Corresponding publication: https://doi.org/10.1175/2008MWR2556.1

    """
    def __init__(self):
        self.rho_h = {'rain': 997}
        self.mass_a = {'rain': np.pi/6*self.rho_h['rain']}
        self.mass_b = {'rain': 3}
        self.mu_param = {'rain': 0}

    def get_psd(self, hm_name, diam, q_mass, q_number):
        """Calculate PSD

        Calculates particle size distributions that are in the form of a gamma distribution.

        Args:
            hm_name (str): Name of hydrometeor class.
            diam (float): Particle diameter for which the number concentration will be returned.
            q_mass (float or ~numpy.ndarray): Mass mixing ratio.
            q_number (float or ~numpy.ndarray): Number concentration mixing ratio.

        Returns:
            float or ~numpy.ndarray:
                Number of particles of the given particle diameter (Particles/(kg*m).

        """
        assert hm_name == "rain", "Only rain PSD possible at the moment"
        lam = self._get_slope(hm_name, q_mass, q_number)
        n_0 = self._get_intercept(hm_name, q_number, lam)
        psd = n_0 * diam**self.mu_param[hm_name] * np.exp(-lam * diam)
        return psd

    def _get_slope(self, hm_name, q_mass, q_number):
        nom = self.mass_a[hm_name] * q_number * math.gamma(self.mu_param[hm_name]
                                                           + self.mass_b[hm_name] + 1)
        denom = q_mass * math.gamma(self.mu_param[hm_name] + 1)
        lam = (nom/denom)**(1/self.mass_b[hm_name])
        return lam

    def _get_intercept(self, hm_name, q_number, lam):
        n_0 = q_number*lam**(self.mu_param[hm_name] + 1) / (math.gamma(self.mu_param[hm_name] + 1))
        return n_0


class MP28:
    """Thompson 2-moment aerosol aware scheme

    Corresponding publication: https://doi.org/10.1175/JAS-D-13.0305.1

    """
    def __init__(self):
        self.rho_h = {'rain': 1000}
        self.mass_a = {'rain': np.pi/6*self.rho_h['rain']}
        self.mass_b = {'rain': 3}
        self.mu_param = {'rain': 0}

    def get_psd(self, hm_name, diam, q_mass, q_number):
        """Calculate PSD

        Calculates particle size distributions that are in the form of a gamma distribution.

        Args:
            hm_name (str): Name of hydrometeor class.
            diam (float): Particle diameter for which the number concentration will be returned.
            q_mass (float or ~numpy.ndarray): Mass mixing ratio.
            q_number (float or ~numpy.ndarray): Number concentration mixing ratio.

        Returns:
            float or ~numpy.ndarray:
                Number of particles of the given particle diameter (Particles/(kg*m).

        """
        assert hm_name == "rain", "Only rain PSD possible at the moment"
        lam = self._get_slope(hm_name, q_mass, q_number)
        n_0 = self._get_intercept(hm_name, q_mass, q_number)
        psd = n_0 * diam**self.mu_param[hm_name] * np.exp(-lam * diam)
        return psd

    def _get_slope(self, hm_name, q_mass, q_number):
        cre2 = self.mu_param[hm_name] + 1
        cre3 = self.mass_b[hm_name] + self.mu_param[hm_name] + 1
        crg2 = math.gamma(cre2)
        crg3 = math.gamma(cre3)
        lam = ((self.mass_a[hm_name]*crg3/crg2)*q_number/q_mass)**(1/3)
        return lam

    def _get_intercept(self, hm_name, q_mass, q_number):
        lam = self._get_slope(hm_name, q_mass, q_number)
        cre2 = self.mu_param[hm_name] + 1
        crg2 = math.gamma(cre2)
        n_0 = q_number * 1/crg2 * lam**cre2
        return n_0


class MP30:
    """Spectral bin scheme

    Corresponding publication: https://doi.org/10.1029/2019JD030576

    """
    def __init__(self):
        self.rho_h = {'rain': 1000}
        self.hm_name_ids = {'rain': 1}

    def get_psd(self, hm_name, wrfmp, ind, thresh=None):
        """Getting particle size distribution

        This method opens the wrfmp dataset that contains the mixing ratio of the input hydrometeor
        class for each bin. The PSD is calculated from this mixing ratio by dividing through the
        bin mass (mass of a single particle within this bin) and then dividing by the bin size to
        norm the PSD with the bin size.

        .. note::

            Rain and cloud have the same bins, but the first 17 correspond to cloud and the
            latter 16 correspond to rain.

        Args:
            hm_name (str): Name of hydrometeor class (clouds, rain, snow, ice, graupel).
            wrfmp (~xarray.Dataset): WRFMP dataset containing the bin mixing ratios.
            ind (tuple): Index of data array at which the psd will be returned.
            thresh (float): All mixing ratio below this threshold will be masked.

        Returns:
            ~numpy.ndarray:
                Array of PSD at input index. Unit of PSD is 1/(kg m) which corresponds to particle
                number per kg of air per particle diameter.

        """
        assert hm_name == "rain", "Only rain PSD possible at the moment"
        psd = []
        drop_d = get_diameters()
        drop_m = self.rho_h[hm_name]*4/3*np.pi*(drop_d/2)**3
        bins = np.arange(17, 33)
        for i in bins:
            # Bin width is half of difference to lower bin + half of difference to upper bin
            bin_d = ((drop_d[i] - drop_d[i - 1]) + (drop_d[i + 1] - drop_d[i]))/2
            # rain_id '1' corresponds to bin_id '0', because python array counts from 0,
            # but rain_id from 1 --> rain_id = i+1
            mp_str = "ff" + str(self.hm_name_ids[hm_name]) + "i" + f"{i+1:02d}"
            q_mass = wrfmp[mp_str][0][ind].values
            if thresh:
                q_mass = np.where(q_mass >= thresh, q_mass, np.nan)
            q_number = q_mass/drop_m[i]/bin_d
            psd.append(q_number)
        return np.array(psd)


class MP50:
    """Predicted Particle Property (P3) scheme

    Corresponding publication: https://doi.org/10.1175/JAS-D-14-0065.1

    """
    def __init__(self):
        self.rho_h = {'rain': 1000}
        self.mu_param = {'rain': 0}

    def get_psd(self, hm_name, diam, q_mass, q_number):
        """Calculate PSD

        Calculates particle size distributions that are in the form of a gamma distribution.

        Args:
            hm_name (str): Name of hydrometeor class.
            diam (float): Particle diameter for which the number concentration will be returned.
            q_mass (float or ~numpy.ndarray): Mass mixing ratio.
            q_number (float or ~numpy.ndarray): Number concentration mixing ratio.

        Returns:
            float or ~numpy.ndarray:
                Number of particles of the given particle diameter (Particles/(kg*m).

        """
        assert hm_name == "rain", "Only rain PSD possible at the moment"
        lam = self._get_slope(hm_name, q_mass, q_number)
        q_number, lam = self._apply_limiters(lam, q_mass, q_number, hm_name)  # P3 applies limiters
        n_0 = self._get_intercept(hm_name, q_number, lam)
        psd = n_0 * diam**self.mu_param[hm_name] * np.exp(-lam * diam)
        return psd

    def _apply_limiters(self, lam, q_mass, q_number, hm_name):
        """Apply rain limiters

        In the P3 code, there is a rain limiter applied, if lam is outside a given range. Then lam
        is put back into the range and q_number is adjusted too.

        """
        lam_max = (self.mu_param[hm_name] + 1)*10**5
        lam_min = (self.mu_param[hm_name] + 1)*1250
        cons1 = np.pi*self.rho_h[hm_name]/6
        lam_lim = np.where(lam < lam_min, lam_min, lam)
        lam_lim = np.where(lam > lam_max, lam_max, lam_lim)
        qn_limit = np.exp(3 * np.log(lam_lim) + np.log(q_mass)
                          + np.log(math.gamma(self.mu_param[hm_name] + 1)) -
                          np.log(math.gamma(self.mu_param[hm_name] + 4))) / cons1
        q_number = np.where(lam < lam_min, qn_limit, q_number)
        q_number = np.where(lam > lam_max, qn_limit, q_number)
        return q_number, lam_lim

    def _get_slope(self, hm_name, q_mass, q_number):
        lam = (np.pi/6 * self.rho_h[hm_name] * q_number * (self.mu_param[hm_name] + 3)
               * (self.mu_param[hm_name] + 2) * (self.mu_param[hm_name] + 1)/q_mass)**(1/3)
        return lam

    def _get_intercept(self, hm_name, q_number, lam):
        n_0 = q_number*lam**(self.mu_param[hm_name] + 1) / (math.gamma(self.mu_param[hm_name] + 1))
        return n_0


def get_diameters():
    """Get diameter bins

    Calculates the bins according to the spectral bin scheme that uses mass-doubling bins. For
    rain, they start at d=0.2mm and go up to 3.3 mm.

    Returns:
        ~numpy.ndarray:
            Array of drop diameters corresponding to spectral bin mass-doubling bins (m).

    """
    mass = 1000*4/3*np.pi*(2*10**(-6))**3  # Mass of 2µm water droplet
    bins = []
    rho = 1000
    for _ in range(33):
        bins.append(((3*mass)/(4*rho*np.pi))**(1/3) * 2)
        mass = 2*mass
    # Append 9000 µm, because that is the maximum considered in CR-SIM.
    # Not available in SBM. Bulk parameterizations are in principle unlimited.
    bins = bins + [0.009]
    return np.array(bins)
