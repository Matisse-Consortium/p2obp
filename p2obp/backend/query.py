import time
from typing import Optional, Dict, List

import astropy.units as u
from astropy.table import Table
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier


SIMBAD_FIELDS = ["mk", "sp", "sptype", "fe_h",
                 "pm", "plx", "rv_value",
                 "flux(U)", "flux_error(U)",
                 "flux(B)", "flux_error(B)",
                 "flux(V)", "flux_error(V)",
                 "flux(R)", "flux_error(R)",
                 "flux(I)", "flux_error(I)",
                 "flux(J)", "flux_error(J)",
                 "flux(H)", "flux_error(H)",
                 "flux(K)", "flux_error(K)"]

CATALOGS = {"gaia": {"catalog": "I/345/gaia2"},
            "tycho": {"catalog": "I/350/tyc2tdsc",
                      "columns": ["*", "e_BTmag", "e_VTmag"]},
            "nomad": {"catalog": "I/297/out"},
            "2mass": {"catalog": "II/246/out"},
            "wise": {"catalog": "II/311/wise"},
            "mdfc": {"catalog": "II/361/mdfc-v10", "columns": ["**"]}}

# TODO: Maybe lists so that multiple things can be queried?
QUERIES = {"gaia": ["Gmag"], "tycho": ["VTmag"],
           "nomad": ["Vmag"], "2mass": ["Jmag"],
           "wise": ["W1mag", "W3mag"],
           "mdfc": ["med-Lflux", "med-Nflux"],
           "simbad": ["RA", "DEC", "FLUX_V"]}


# TODO: Make function that removes all None keys from the dictionary
def get_best_match(catalog_table: Table, query_keys: List) -> Table:
    """Gets the best match from the catalog entries

    Parameters
    ----------
    catalog_table : Table
        The table containing the queried catalog's results.
    query_keys : List
        The keys that are queried.

    Returns
    -------
    best_match : Table
        The best match from the queried catalog's table.
    """
    best_matches = {}
    for query_key in query_keys:
        if query_key in catalog_table.columns:
            # TODO: Handle case of empty catalog? -> Check that
            if len(catalog_table) == 1:
                best_matches[query_key] = catalog_table[query_key][0]
            else:
                # NOTE: Get lowest element in case magnitude is queried
                if "mag" in query_key:
                    best_matches[query_key] = catalog_table[query_key].min()
                best_matches[query_key] = catalog_table[query_key].max()
    return best_matches


def get_catalog(name: str, catalog: str,
                match_radius: u.arcsec = 5.):
    """Queries the specified catalog.

    Parameters
    ----------
    name : str
        The target's name.
    catalog : str
        The catalog's name.
    match_radius : astropy.units.arcsec
        The radius in which is queried.
        Default is 5.

    Returns
    -------
    catalog_table : Table
        The table containing the queried catalog's results.
    """
    if not isinstance(match_radius, u.Quantity):
        match_radius *= u.arcsec
    else:
        if match_radius.unit != u.arcsec:
            raise ValueError("The match radius has to be in"
                             " astropy.units.arcsecond.")

    if catalog == "simbad":
        query_site = Simbad()
        query_site.add_votable_fields(*SIMBAD_FIELDS)
        catalog_table = query_site.query_object(name)
    else:
        # CHECK: Does this always return a table list?
        query_site = Vizier(**CATALOGS[catalog])
        catalog_table = query_site.query_object(name, radius=match_radius)[0]
    return catalog_table


def query(name: str,
          catalogs: Optional[List] = None,
          match_radius: Optional[float] = 5.,
          sleep_time: float = 0.1) -> Dict:
    """Queries an astronomical target by its name from 

    Parameters
    ----------
    name : str
        The target's name.
    catalogs : list, optional
        The catalog's name.
    match_radius : float, optional
        The radius in which is queried.
        Default is 5.

    Returns
    -------
    target : dict
        The target's queried information.
    """
    target = {}
    if catalogs is None:
        catalogs = [*CATALOGS.keys()]

    for catalog in catalogs:
        catalog_table = get_catalog(name, catalog, match_radius)
        target = {**target, **get_best_match(catalog_table, QUERIES[catalog])}
        time.sleep(sleep_time)
    return target