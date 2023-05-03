from pathlib import Path
from typing import Union, Optional, Dict, Tuple

import astropy.units as u
import pkg_resources
import toml
from astropy.coordinates import SkyCoord

from .query import query
from .options import options
from .utils import convert_proper_motions

# TODO: Include log message if nan has been replaced
# TODO: Exchange, possibly slow function?
TEMPLATE_FILE = Path(pkg_resources.resource_filename("p2obp", "data/templates.toml"))


def load_template(file: Path,
                  header: str,
                  sub_header: Optional[str] = None,
                  operational_mode: Optional[str] = None) -> Dict:
    """Loads a template from a (.toml)-file.

    Parameters
    ----------
    file : path
        A (.toml)-file containing templates.
    header : str
        The name of the specific template.
    sub_header : str, optional
        The name of a sub-template.
    operational_mode : str, optional
        The mode in which MATISSE is operated, either
        "gra4mat" or "matisse".

    Returns
    -------
    template : dict
        A dictionary that is the template.
    """
    with open(file, "r+", encoding="utf-8") as toml_file:
        if operational_mode is not None:
            return toml.load(toml_file)[operational_mode][header]
        return toml.load(toml_file)[header][sub_header]


def write_dict(file, dictionary: Dict):
    """Iterates over the key and value pairs of a
    dictionary and writes them."""
    for key, value in dictionary.items():
        file.write(f'{key.ljust(40)}"{str(value)}"'+"\n")


def write_ob(ob: Dict, ob_name: str, output_dir: Path) -> None:
    """Writes the (.obx)-file to the specified directory"""
    out_file = Path(output_dir) / f"{ob_name}.obx"
    with open(out_file, "w+", encoding="utf-8") as obx_file:
        for dictionary in ob.values():
            if any(isinstance(value, dict) for value in dictionary.values()):
                for sub_dict in dictionary.values():
                    write_dict(obx_file, sub_dict)
                    obx_file.write("\n\n")
            else:
                write_dict(obx_file, dictionary)
                obx_file.write("\n\n")
    # TODO: Make this a better message or a function
    print(f"Created OB: '{ob_name}'.")


def set_ob_name(target: Union[Dict, str],
                observation_type: str,
                sci_name: Optional[str] = None,
                tag: Optional[str] = None) -> str:
    """Sets the OB's name.

    Parameters
    ----------
    target : dict or str
    observation_type : str
    sci_name : str, optional
    tag : str, Optional

    Returns
    -------
    ob_name : str

    Examples
    --------
    """
    ob_name = f"{observation_type.upper()}"
    if isinstance(target, dict):
        ob_name += f"_{target['name'].replace(' ', '_')}"
    else:
        ob_name += f"_{target.replace(' ', '_')}"
    if sci_name is not None:
        ob_name += f"_{sci_name.replace(' ', '_')}"
    return ob_name if tag is None else f"{ob_name}_{tag}"


def set_resolution_and_dit(resolution: str,
                           operational_mode: str,
                           array_configuration: str) -> Tuple[str, float]:
    """

    Parameters
    ----------
    resolution : str
    operational_mode : str
    array_configuration : str

    Returns
    -------
    resolution : str
    dit : float
    """
    array = "uts" if "ut" in array_configuration else "ats"
    key = f"dit.{operational_mode}.{array}.{resolution}"
    return resolution.upper(), options[key]


def format_proper_motions(target: Dict) -> Tuple[float, float]:
    """Correctly formats the right ascension's and declination's
    proper motions."""
    return convert_proper_motions(target["PMRA"], target["PMDEC"])


def format_ra_and_dec(target: Dict) -> Tuple[str, str]:
    """Correclty formats the right ascension and declination."""
    coordinates = SkyCoord(f"{target['RA']} {target['DEC']}",
                           unit=(u.hourangle, u.deg))
    ra_hms = coordinates.ra.to_string(unit=u.hourangle, sep=":",
                                      pad=True, precision=3)
    dec_dms = coordinates.dec.to_string(sep=":", pad=True,
                                        precision=3)
    return ra_hms, dec_dms


# CHECK: Implement some way to show that flux has been not set?
def format_fluxes(target: Dict) -> Tuple[float, float]:
    """Correctly gets and formats the fluxes from the queried data."""
    flux_lband, flux_nband = None, None
    lband_keys, nband_keys = ["med-Lflux", "W1mag"], ["med-Nflux", "W3mag"]

    for lband_key, nband_key in zip(lband_keys, nband_keys):
        if lband_key in target and flux_lband is None:
            flux_lband = target[lband_key]
            if "mag" in lband_key:
                flux_lband = 309.54 * 10.0**(-flux_lband/2.5)

        if nband_key in target and flux_nband is None:
            flux_nband = target[nband_key]
            if "mag" in nband_key:
                flux_nband = 31.674 * 10.0**(-flux_nband/2.5)
    flux_lband = round(flux_lband, 2) if flux_lband is not None else flux_lband
    flux_nband = round(flux_nband, 2) if flux_nband is not None else flux_nband
    return flux_lband, flux_nband


def fill_header(target: Dict,
                observation_type: str,
                array_configuration: str,
                sci_name: Optional[str] = None,
                tag: Optional[str] = None) -> Dict:
    """Fills in the header dictionary with the information from the query.

    Parameters
    ----------
    target : dict
    observation_type : str
    array_configuration : str
    sci_name : str, optional
    tag : str, optional

    Returns
    -------
    header : dict
    """
    header = {}
    header_user = load_template(TEMPLATE_FILE,
                                "header", sub_header="user")
    header_target = load_template(TEMPLATE_FILE,
                                  "header", sub_header="target")
    header_constraints = load_template(TEMPLATE_FILE,
                                       "header", sub_header="constraints")
    header_observation = load_template(TEMPLATE_FILE,
                                       "header", sub_header="observation")
    ob_name = set_ob_name(target, observation_type, sci_name, tag)
    ra_hms, dec_dms = format_ra_and_dec(target)
    prop_ra, prop_dec = format_proper_motions(target)

    header_user["name"] = ob_name
    header_target["TARGET.NAME"] = target["name"].replace(' ', '_')
    header_target["ra"], header_target["dec"] = ra_hms, dec_dms
    header_target["propRA"], header_target["propDec"] = prop_ra, prop_dec

    if "ut" in array_configuration:
        header_constraints["moon_angular_distance"] = 10

    header_observation["OBSERVATION.DESCRIPTION.NAME"] = ob_name

    header["user"] = header_user
    header["target"] = header_target
    header["constraints"] = header_constraints
    header["observation"] = header_observation
    return header


def fill_acquisition(target: Dict,
                     operational_mode: str,
                     array_configuration: str) -> Dict:
    """Gets the for the operational mode correct acquisition template
    and then fills it in with the information from the query.

    Parameters
    ----------
    target : dict
    operational_mode : str
    array_configuration : str

    Returns
    -------
    acquisition : dict
    """
    acquisition = load_template(TEMPLATE_FILE, "acquisition",
                                operational_mode=operational_mode)
    flux_lband, flux_nband = format_fluxes(target)

    if "GSmag" in target:
        acquisition["COU.GS.MAG"] = target["GSmag"]
    elif "Vmag" in target:
        acquisition["COU.GS.MAG"] = target["Vmag"]
    elif "FLUX_V" in target:
        acquisition['COU.GS.MAG'] = target["FLUX_V"]

    if "ut" in array_configuration:
        array_configuration = "UTs"

    acquisition["ISS.BASELINE"] = array_configuration

    # TODO: Make logger here
    if flux_lband is not None:
        acquisition['SEQ.TARG.FLUX.L'] = flux_lband
    if flux_nband is not None:
        acquisition['SEQ.TARG.FLUX.N'] = flux_nband

    acquisition["SEQ.TARG.MAG.K"] = round(target["Kmag"], 2)

    if operational_mode == "gra4mat":
        acquisition["SEQ.TARG.MAG.H"] = round(target["Hmag"], 2)
    return acquisition


def fill_observation(resolution: str,
                     observation_type: str,
                     operational_mode: str,
                     array_configuration: str) -> Dict:
    """Gets the for the operational mode correct acquisition template
    and then fills it in with the information from the query.

    Parameters
    ----------
    resolution : str
    observation_type : str
    operational_mode : str
    array_configuration : str

    Returns
    -------
    acquisition : dict
    """
    observation = load_template(TEMPLATE_FILE, "observation",
                                operational_mode=operational_mode)
    resolution, dit = set_resolution_and_dit(resolution, operational_mode,
                                             array_configuration)
    observation_type = "SCIENCE" if observation_type == "sci" else "CALIB"
    observation["DPR.CATG"] = observation_type
    observation["INS.DIL.NAME"] = resolution
    observation["DET1.DIT"] = dit
    observation["SEQ.DIL.WL0"] = options["central_wl"]
    return observation


# TODO: Move the output dir to create_ob
def compose_ob(target_name: str,
               observational_type: str,
               array_configuration: str,
               operational_mode: Optional[str] = "st",
               sci_name: Optional[str] = None,
               tag: Optional[str] = None,
               resolution: Optional[str] = "low",
               ):
    """Composes the dictionary

    Parameters
    ----------
    target_name : str
    observational_type : str
    array_configuration : str
        Determines the array configuration. Possible values are "UTs",
        "small", "medium", "large", "extended".
    operational_mode : str, optional
        The mode of operation for MATISSE. Can be either "st"/"standalone"
        for the MATISSE-standalone mode or "gr"/"gra4mat" for GRA4MAT.
        Default is standalone.
    sci_name : str, optional
    tag : str, optional
    resolution : str, optional
    """
    array_configuration = array_configuration.lower()
    if array_configuration not in ["uts", "small", "medium", "large", "extended"]:
        raise IOError("Unknown array configuration provided!"
                      " Choose from 'UTs', 'small', 'medium',"
                      " 'large' or 'extended'.")

    observational_type = observational_type.lower()
    if observational_type not in ["sci", "cal"]:
        raise IOError("Unknown observation type provided!"
                      " Choose from 'SCI' or 'CAL', for "
                      "a science target or a calibrator.")

    operational_mode = operational_mode.lower()
    if operational_mode in ["st", "standalone"]:
        operational_mode = "matisse"
    elif operational_mode in ["gr", "gra4mat"]:
        operational_mode = "gra4mat"
    else:
        raise IOError("Unknown operational mode provided!"
                      " Choose from 'st'/'standalone' or"
                      " 'gr'/'gra4mat'.")

    resolution = resolution.lower()
    if resolution not in ["low", "med", "high"]:
        raise IOError("Unknown resolution provided!"
                      " Choose from 'low', 'med' or 'high'.")

    target = query(target_name)
    header = fill_header(target, observational_type,
                         array_configuration, sci_name, tag)

    acquisition = fill_acquisition(target,
                                   operational_mode,
                                   array_configuration)

    observation = fill_observation(resolution, observational_type,
                                   operational_mode, array_configuration)

    return {"header": header,
            "acquisition": acquisition, "observation": observation}