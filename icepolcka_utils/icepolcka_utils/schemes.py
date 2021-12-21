"""Microphysical schemes

This module contains a class for each of the microphysical schemes used in my
analyses. These classes provide some functionality such as calculating
terminal velocity etc.

Classes:
    :class:`.MPScheme`: Abstract super class for all microphysic schemes.
    :class:`.MP8`: Specific class for Thompson 2-moment scheme.
    :class:`.MP10`: Specific class for Morrison 2-moment scheme.
    :class:`.MP28`: Specific class for Thompson 2-moment aerosol-aware scheme.
    :class:`.MP30`: Specific class for spectral bin scheme (Shpund et al 2019)
    :class:`.MP50`: Specific class for P3 scheme.

"""
import math
import numpy as np


class MPScheme(object):
    """Abstract microphysic schemes class

    This is the main super class for all microphysic schemes. It follows an
    abstract factory pattern.

    The following methods are available to all subclasses:
    - :meth:`get_terminal_velocity`:
        Returns terminal velocity.

    """


class MP8(MPScheme):
    """Thompson 2-moment scheme

    Specific subclass of :class:`MPScheme`: for the Thompson 2-moment scheme:
    https://doi.org/10.1175/2008MWR2387.1

    """
    def __init__(self):
        self.id = 8
        self.r_gas = 287.04
        self.rho_h = {
            'rain': 1000,
            }
        self.a = {
            'rain': np.pi/6*self.rho_h['rain'],
            }
        self.b = {
            'rain': 3,
            }
        self.alpha = {
            'rain': 4854,
            }
        self.beta = {
            'rain': 1,
            }
        self.f = {
            'rain': 195,
            }
        self.COF = [76.18009172947146, -86.50532032941677, 24.01409824083091,
                    -1.231739572450155, 0.1208650973866179*10**(-2),
                    -0.5395239384953*10**(-5)]

    def get_psd(self, hm, d, qr, qn, qv, p, t):
        if hm == "rain":
            lam = self.get_slope(hm, qr, qn)
            n_0 = self.get_intercept(hm, qr, qn, qv, p, t)
            mu = self.get_shape_parameter(hm)
            psd = n_0 * d**mu * np.exp(-lam * d)
            return psd
        else:
            raise NotImplementedError("Only rain PSD can be calculated")

    def get_ccg(self, cce):
        X = cce
        Y = X
        TMP = X + 5.5
        TMP = (X + 0.5)*np.log(TMP) - TMP
        SER = 1.000000000190015
        STP = 2.5066282746310005
        for i in range(6):
            Y = Y + 1
            SER = SER + self.COF[i]/Y
        gammaln = TMP + np.log(STP*SER/X)
        ccg = np.exp(gammaln)
        return ccg

    def get_slope(self, hm, qr, qn):
        mu = self.get_shape_parameter(hm)
        if hm == "rain":
            cce2 = mu + 1
            cce3 = self.b[hm] + 1
            ccg2 = self.get_ccg(cce2)
            ccg3 = self.get_ccg(cce3)
            lam = ((self.a[hm]*ccg3/ccg2)*qn/qr)**(1/3)
            return lam
        else:
            raise NotImplementedError("Only rain slope can be calculated")

    def get_intercept(self, hm, qr, qn, qv, p, t):
        mu = self.get_shape_parameter(hm)
        rho = self.get_density(p, t, qv)
        if hm == "rain":
            cce2 = mu + 1
            ccg2 = self.get_ccg(cce2)
            lam = self.get_slope(hm, qr, qn)
            n0 = qn*rho/ccg2 * lam**cce2
            return n0
        else:
            raise NotImplementedError("Only rain intercept can be calculated")

    @staticmethod
    def get_shape_parameter(hm):
        if hm == "rain":
            return 0
        else:
            raise NotImplementedError("Only rain shape parameter can be "
                                      "calculated")

    def get_n0_exp(self, rg):
        ygra1 = np.log10(max(10**(-9), rg))
        zans1 = (3.5 + 2 / 7 * (ygra1 + 7))
        zans1 = max(2, min(zans1, 7))
        n0_exp = 10**zans1
        return n0_exp

    def get_density(self, p, t, qv):
        return 0.622 * p / (self.r_gas * t) * (qv + 0.622)


class MP10(MPScheme):
    """Morrison 2-moment scheme

    Specific subclass of :class:`MPScheme`: for the Morrison 2-moment scheme:
    https://doi.org/10.1175/2008MWR2556.1

    """
    def __init__(self):
        self.id = 10
        self.rho_h = {
            'rain': 997,
            }
        self.a = {
            'rain': np.pi/6*self.rho_h['rain'],
            }
        self.b = {
            'rain': 3,
            }
        self.alpha = {
            'rain': 841.99667,
            }
        self.beta = {
            'rain': 0.8,
            }

    def get_psd(self, hm, d, n, q):
        if hm == "rain":
            lam = self.get_slope(hm, n, q)
            n_0 = self.get_intercept(hm, n, lam)
            mu = self.get_shape_parameter(hm)
            psd = n_0 * d**mu * np.exp(-lam * d)
            return psd
        else:
            raise NotImplementedError("Only rain PSD can be calculated")

    def get_slope(self, hm, n, q):
        mu = self.get_shape_parameter(hm)
        nom = self.a[hm] * n * math.gamma(mu + self.b[hm] + 1)
        denom = q * math.gamma(mu + 1)
        lam = (nom/denom)**(1/self.b[hm])
        return lam

    def get_intercept(self, hm, n, lam):
        mu = self.get_shape_parameter(hm)
        n_0 = n*lam**(mu + 1) / (math.gamma(mu + 1))
        return n_0

    def get_shape_parameter(self, hm):
        if hm == "rain":
            return 0
        else:
            raise NotImplementedError("Only rain shape parameter can be "
                                      "calculated")


class MP28(MPScheme):
    """Thompson 2-moment aerosol aware scheme

    Specific subclass of :class:`MPScheme`: for the Thompson 2-moment
    aerosol-aware scheme: https://doi.org/10.1175/JAS-D-13.0305.1

    """
    def __init__(self):
        self.id = 8
        self.r_gas = 287.04
        self.rho_h = {
            'rain': 1000,
            }
        self.a = {
            'rain': np.pi/6*self.rho_h['rain'],
            }
        self.b = {
            'rain': 3,
            }
        self.alpha = {
            'rain': 4854,
            }
        self.beta = {
            'rain': 1,
            }
        self.f = {
            'rain': 195,
            }
        self.COF = [76.18009172947146, -86.50532032941677, 24.01409824083091,
                    -1.231739572450155, 0.1208650973866179*10**(-2),
                    -0.5395239384953*10**(-5)]

    def get_psd(self, hm, d, qr, qn, qv, p, t):
        if hm == "rain":
            lam = self.get_slope(hm, qr, qn)
            n_0 = self.get_intercept(hm, qr, qn, qv, p, t)
            mu = self.get_shape_parameter(hm)
            psd = n_0 * d**mu * np.exp(-lam * d)
            return psd
        else:
            raise NotImplementedError("Only rain PSD can be calculated")

    def get_ccg(self, cce):
        X = cce
        Y = X
        TMP = X + 5.5
        TMP = (X + 0.5)*np.log(TMP) - TMP
        SER = 1.000000000190015
        STP = 2.5066282746310005
        for i in range(6):
            Y = Y + 1
            SER = SER + self.COF[i]/Y
        gammaln = TMP + np.log(STP*SER/X)
        ccg = np.exp(gammaln)
        return ccg

    def get_slope(self, hm, qr, qn):
        mu = self.get_shape_parameter(hm)
        if hm == "rain":
            cce2 = mu + 1
            cce3 = self.b[hm] + 1
            ccg2 = self.get_ccg(cce2)
            ccg3 = self.get_ccg(cce3)
            lam = ((self.a[hm]*ccg3/ccg2)*qn/qr)**(1/3)
            return lam
        else:
            raise NotImplementedError("Only rain slope can be calculated")

    def get_intercept(self, hm, qr, qn, qv, p, t):
        mu = self.get_shape_parameter(hm)
        rho = self.get_density(p, t, qv)
        if hm == "rain":
            cce2 = mu + 1
            ccg2 = self.get_ccg(cce2)
            lam = self.get_slope(hm, qr, qn)
            n0 = qn*rho/ccg2 * lam**cce2
            return n0
        else:
            raise NotImplementedError("Only rain intercept can be calculated")

    def get_shape_parameter(self, hm):
        if hm == "rain":
            return 0
        else:
            raise NotImplementedError("Only rain shape parameter can be "
                                      "calculated")

    def get_n0_exp(self, rg):
        ygra1 = np.log10(max(10**(-9), rg))
        zans1 = (3.5 + 2 / 7 * (ygra1 + 7))
        zans1 = max(2, min(zans1, 7))
        n0_exp = 10**zans1
        return n0_exp

    def get_density(self, p, t, qv):
        return 0.622 * p / (self.r_gas * t) * (qv + 0.622)


class MP30(MPScheme):
    """Spectral bin scheme

    Specific subclass of :class:`MPScheme`: for the spectral bin scheme:
    https://doi.org/10.1029/2019JD030576

    """
    def __init__(self):
        self.id = 30
        self.rho_h = {
            'rain': 1000,
            }
        self.hm_ids = {
            'rain': 1,  # Rain and cloud have same id (cloud <= bin 16 < rain)
            }

    def get_bins(self, hm):
        if hm == "rain":
            m = 1000*4/3*np.pi*(2*10**(-6))**3  # Mass of 2µm water droplet
            bins = []
            rho = self.rho_h[hm]
            for i in range(33):
                bins.append(((3*m)/(4*rho*np.pi))**(1/3))
                m = 2*m
            return np.array(bins)
        else:
            raise NotImplementedError("Only rain PSD can be calculated")

    def get_psd(self, hm, wrfmp, i_height=":", i_lon=":", i_lat=":"):
        """Getting particle size distribution

        This method opens the wrfmp dataset that contains the mixing ratio of
        input hydrometeor class for each bin. The PSD is calculated from this
        mixing ratio by dividing through the bin mass (mass of a single
        particle within this bin) and then dividing by the bin size to norm
        the PSD with the bin size.

        Note: Rain and cloud have the same bins, but the first 17 correspond
        to cloud and the latter 16 correspond to rain.

        Args:
            hm (string): Name of hydrometeor class (clouds, rain, snow, ice,
                graupel).
            wrfmp (xarray.Dataset): WRFMP dataset containing the bin mixing
                ratios.
            i_height (int): Height index at which PSD shall be returned.
            i_lon (int): Lon index at which PSD shall be returned.
            i_lat (int): Lat index at which PSD shall be returned.

        Returns:
            np.ndarray: Array of PSD at input index. Unit of PSD is 1/(kg m)
                which corresponds to Particle number per kg of air per particle
                diameter.
        """
        psd = []
        bin_r = self.get_bins(hm)
        bin_m = self.rho_h[hm]*4/3*np.pi*bin_r**3
        if hm == "rain":
            bins = np.arange(18, 34)
        else:
            raise NotImplementedError("Only rain PSD can be calculated")
        for i in bins:
            try:
                bin_d = (bin_r[i] - bin_r[i - 1])*2
            except IndexError:
                bin_d = bin_d
            mp_str = "ff" + str(self.hm_ids[hm]) + "i" + f"{i:02d}"
            Q = wrfmp[mp_str][0][i_height, i_lon, i_lat].values
            N = Q/bin_m[i - 1]/bin_d
            psd.append(N)
        return np.array(psd)


class MP50(MPScheme):
    """Predicted Particle Property (P3) scheme

    Specific subclass of :class:`MPScheme`: for the Predicted Particle
    Property (P3) bulk microphysics scheme:
    https://doi.org/10.1175/JAS-D-14-0065.1

    """
    def __init__(self):
        self.id = 50
        self.rho_h = {
            'rain': 1000,
            }

    def get_psd(self, hm, d, n, q):
        if hm == "rain":
            lam = self.get_slope(hm, n, q)
            n_0 = self.get_intercept(hm, n, lam)
            mu = self.get_shape_parameter(hm)
            psd = n_0 * d**mu * np.exp(-lam * d)
            return psd
        else:
            raise NotImplementedError("Only rain PSD can be calculated")

    def get_slope(self, hm, n, q):
        """Calculate slope parameter of PSD

        Took formula from CRSIM which is the same as in WRF code, but seems to
        differ from paper.

        Only works for rain right now.

        Args:
            hm (string): Name of hydrometeor class.
            n (float): Total number concentration [1/kg].
            q (float): Total mixing ratio [kg/kg]

        """
        if hm == "rain":
            mu = self.get_shape_parameter(hm)
            lam = (np.pi/6*self.rho_h[hm]*n*(mu + 3)*(mu + 2)*(mu + 1)/q)**(1/3)
            lam = min((mu + 1)*10**5, lam)
            lam = max((mu + 1)*1250, lam)
        else:
            raise NotImplementedError("Only rain slope can be calculated")
        return lam

    def get_intercept(self, hm, n, lam):
        if hm == "rain":
            mu = self.get_shape_parameter(hm)
            n_0 = n*lam**(mu + 1) / (math.gamma(mu + 1))
            return n_0
        else:
            raise NotImplementedError("Only rain intercept can be calculated")

    def get_shape_parameter(self, hm):
        if hm == "rain":
            return 0
        else:
            raise NotImplementedError("Only rain shape parameter can be "
                                      "calculated")

