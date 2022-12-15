"""OB Uploader

This script makes the main folders for a MATISSE run in P2, i.e., the nights in
which are observed, the mode in which is observed (GRA4MAT or standalone) and
the subfolders 'main_targets' and 'backup_targets'. Additionally, under the
'main_targets'-folder it creates a folder for every SCI-OB, and imports the
SCI-OB as well as the corresponding CALs into the folder.

DISCLAIMER: Guaranteed for working only in conjunction with the 'parseOBplan'
and the 'automaticOBcreation' scripts, as they format the folders correctly.

The structure that the folder of the given path need to be in is the following:
    >>> path/<GRA4MAT_ft_vis or standalone>/<run>/<night>/*.obx

This is automatically the case if the folders are made with the above mentioned
scripts.

This file can also be imported as a module and contains the following functions:
    * get_corresponding_run - Gets a run corresponding to an input List
    * create_remote_folder - Creates a folder on P2 and returns its ID
    * get_subfolders - Gets all the folders from a directory
    * remote_folder_exists - Checks if a folder with that ID already exists on P2
    * generate_finding_chart_verify - Not yet implemented
    * make_folders_and_upload - Makes the individual folders for the OBs and uses the
    'loadobx' script to import the already made (.obx)-files to P2
    * ob_uploader - The main loop of the script, makes the folders and uploads
    the OBs in a folder to the P2

Example of usage:
    >>> from uploader import ob_uploader

    # The path to the top most folder

    >>> path = "/Users/scheuck/Documents/PhD/matisse_stuff/observation/phase2/obs"

    # The data describing the run

    >>> run_data = ["109", "2313"]

    # The main loop

    >>> ob_uploader(path, "production", ESO_USERNAME, ESO_PASSWORD)
"""
import os
from re import I
import p2api
import warnings

from pathlib import Path
from typing import Dict, List, Optional

import loadobx

# TODO: Make readme template and add additional per night, then upload it
# FIXME: Make generateFindingCharts work and verification as well
# TODO: Add complete hour count for folders that have been made
# -> FIXME: Need fix of folder creation first
# BUG: Folder sorting sometimes doesn't work? -> Check if that persists?


README_TEMPLATE = ...


def remote_container_exists(p2_connection: p2api, container_id: int) -> bool:
    """Checks if the container with this id exists on P2

    Parameters
    ----------
    p2_connection: p2api
        The p2ui python api
    container_id: int
        The id of the container (either run or folder) on the P2

    Returns
    -------
    container_exists: bool
        'True' if container exists, otherwise 'False'
    """
    try:
        if p2_connection.getContainer(container_id):
            return True
    except p2api.p2api.P2Error:
        return False


def get_remote_run(p2_connection: p2api, run_id: str) -> int | None:
    """Gets the run that corresponds to the period, proposal and the number and
    returns its runId

    Parameters
    ----------
    p2_connection: p2api
        The p2ui python api
    run_id: str
        The run's id in the format (period.proposal_tag.run_number)

    Returns
    -------
    run_id: int | None
        The run's Id that can be used to access and modify it with the p2api. If not found
        then None
    """
    for run in p2_connection.getRuns()[0]:
        if run_id == run["progId"]:
            return run["containerId"]
    return None


def upload_obx_to_container(p2_connection: p2api, target: str,
                            obx_files: List[Path], container_id: int) -> None:
    """Uploads (.obx)-files contained in a list to a given container

    Parameters
    ----------
    p2_connection: p2api
        The p2ui python api
    target: str
    obx_files: List[Path]
    container_id: int
    """
    for obx_file in obx_files:
        obx_container_id = create_remote_container(p2_connection, target, container_id)
        loadobx.loadob(p2_connection, obx_file, obx_container_id)


def create_remote_container(p2_connection: p2api, name: str, container_id: int) -> int:
    """Creates a container (either a run or folder) on P2

    Parameters
    ----------
    p2_connection: p2api
        The P2 python api
    name: str
        The folder's name
    container_id: int
        The id that specifies the container (a run or folder on P2)

    Returns
    -------
    container_id: int
        The created container's id
    """
    folder, _ = p2_connection.createFolder(container_id, name)
    print(f"folder: {name} created!")
    return folder["containerId"]


def update_readme():
    ...


def generate_charts_and_verify(p2_connection: p2api, container_id: int) -> None:
    """Generates the finding charts and then verifies all OBs in the container

    p2_connection: p2api
        The p2ui python api
    container_id: int
        The id of the container on the P2
    """
    folders = p2_connection.getItems(container_id)

    for folder in folders[0]:
        obx_files = p2_connection.getItems(folder["containerId"])

        for obx_file in obx_files[0]:
            p2_connection.generateFindingChart(obx_file["obId"])
            print(f"Finding chart created for OB {obx_file['name']}!")

            p2_connection.verifyOB(obx_file["obId"])
            print(f"OB {obx_file['name']} verified!")

    p2_connection.verifyContainer(container_id, True)


# TODO: This function is not used right now  make it into iterative over subfolders
def get_subfolders_containing_files(search_directory: Path,
                                    file_type: Optional[str] = ".obx") -> List[Path]:
    """Recursively searches through the whole subtree of the search directory and returns
    the folders containt the specified filetype as a list of paths

    Parameters
    ----------
    search_path: Path
        The path of the folder of which the subfolders are to be fetched
    file_type: str, optional
        The filetype that is being searched for

    Returns
    -------
    List[Path]
        List of the folders' paths
    """
    directories_with_obx_files = []

    for child in search_directory.rglob(f"*{file_type}"):
        parent_directory = child.parent

        if parent_directory not in directories_with_obx_files:
            directories_with_obx_files.append(parent_directory)

    return [directory.relative_to(search_directory)\
            for directory in directories_with_obx_files]


def sort_science_and_calibrator(science_to_calibrator_dict: Dict) -> Dict:
    """This checks if the science targets or calibrators are made in a sortable way and if
    not just returns the dict, otherwise it sorts them by their appended digit

    Parameters
    -----------
    science_to_calibrator_dict: Dict
        A dictionary containing the "name" of the science target as key and as value a
        list of Paths with all its associated (.obx)-file paths

    Returns
    -------
    science_to_calibrator_dict: Dict
    """
    for science_target, obx_files in science_to_calibrator_dict.items():
        if any([obx_file.stem.endswith(("-a", "-b")) for obx_file in obx_files]):
            science_to_calibrator_dict[science_target] = \
                    sorted(obx_files, key=lambda x: (x.name.find("b") >= 0,
                                                     x.name.find("a") >= 0))[::-1]
    return science_to_calibrator_dict


def pair_science_to_calibrators(upload_directory: Path, obx_folder: Path) -> Dict:
    """Pairs up the science targets and calibrators (.obx)-files into a dict

    Parameters
    ----------
    upload_directory: Path
    obx_folder: Path
        A folder containing (.obx)-files

    Returns
    -------
    sorted_science_and_calibrator_dict: Dict
    """
    science_to_calibrator_dict = {}
    obx_files = (upload_directory / obx_folder).glob("*.obx")
    obx_files = sorted(obx_files, key=lambda x: x.stem.split("-")[1])

    for obx_file in obx_files:
        stem = obx_file.stem
        if "SCI" in stem:
            science_target_name = "_".join([part for part in stem.split("_")[1:]])
            science_to_calibrator_dict[science_target_name] = [obx_file]
        else:
            science_target_of_calibrator = "_".join(stem.split("_")[2:-1])
            science_to_calibrator_dict[science_target_of_calibrator].append(obx_file)

    return sort_science_and_calibrator(science_to_calibrator_dict)


def create_folder_structure_and_upload(p2_connection: p2api,
                                       upload_directory: Path,
                                       obx_folder: Path, run_id: int,
                                       container_ids: Dict, containers: set):
    """

    Parameters
    ----------
    p2_connection: p2api
    upload_directory: Path
    obx_folder: Path
    run_id: int
    container_ids: Dict
    containers: set
    """
    for parent in obx_folder.parents[::-1][1:]:
        if parent in containers:
            continue

        containers.add(parent)
        if (parent.parent != Path(".")) and (parent.parent in containers):
            container_id = create_remote_container(p2_connection,
                                                   parent.name, container_id)
            container_id[parent.parent.name][parent.name] = {"id": container_id}
        else:
            container_id = create_remote_container(p2_connection, parent.name, run_id)
            container_ids[parent.name] = {"id": container_id}

    for target, obx_files in pair_science_to_calibrators(upload_directory, obx_folder).items():
        upload_obx_to_container(p2_connection, target, obx_files, container_id)

    return container_ids, containers


def ob_uploader(upload_directory: Path,
                run_prog_id: Optional[str] = None,
                container_id: Optional[int] = None,
                server: Optional[str] = "production",
                username: Optional[str] = None) -> None:
    """This checks if run is specified or given by the folder names and then
    makes the same folders on the P2 and additional folders (e.g., for the
    'main_targets' and 'backup_targets' as well as for all the SCI-OBs. It then
    uploads the SCI- and CAL-OBs to the P2 as well

    Parameters
    ----------
    upload_directories: List[Path]
        List containing folders for upload
    run_prog_id: str, optional
        The program id of the run. Used to fetch the run to be uploaded to
    container_id: int, optional
        If this is provided then only the subtrees of the upload_directory will be
        given container. This overrides the run_data input
    server: str
        The enviroment to which the (.obx)-file is uploaded, 'demo' for testing,
        'production' for paranal and 'production_lasilla' for la silla
    username: str, optional
        The username for the P2
    """
    # TODO: Make automatic upload possible again
    # p2_connection = loadobx.login(username, None, server)

    if container_id:
        run_id = container_id
    elif run_prog_id:
        run_id = get_remote_run(p2_connection, run_id)
    else:
        raise IOError("Either run-program-id or container-id must be given!")

    obx_folders = get_subfolders_containing_files(upload_directory)

    container_ids, containers = {}, set()
    for obx_folder in obx_folders:
        container_ids, containers =\
                create_folder_structure_and_upload("", obx_folder, run_prog_id,
                                                   container_ids, containers)
    print(container_ids, containers)

    # TODO: Check if function works properly
    # generate_charts_and_verify(p2, mode_folder_id)
    # print(f"Container: {os.path.basename(i)} of {night_name} verified!")


# TODO: Make container id also upload files to an empty folder directly

if __name__ == "__main__":
    path = Path("/Users/scheuck/data/observations/obs/manualOBs")
    run_prog_id = "110.2474.003"
    # ob_uploader(path, run_id, username="MbS")


