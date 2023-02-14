"""The completely automated OB creation from parsing to upload"""
from pathlib import Path
from typing import Dict, List, Optional

from parser import parse_night_plan
from creator import ob_creation
from uploader import ob_uploader
from utils import get_password_and_username


def ob_pipeline(output_dir: Optional[Path] = None,
                manual_lst: Optional[List] = None,
                night_plan_path: Optional[Path] = None,
                mode_selection: str = "gr",
                resolution_dict: Optional[Dict] = {},
                save_yaml_file: Optional[bool] = False,
                upload: Optional[bool] = False) -> None:
    """

    Parameters
    ----------
    output_dir: Path, optional
    upload: bool, optional
    night_plan_path: Path, optional
    resolution_dict: Dict, optional
    save_yaml_file: bool, optional
    upload: bool, optional
    """
    output_dir = output_dir if output_dir else Path().cwd()
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    # TODO: At some point exchange this with proper password getter
    if upload:
        username, password = get_password_and_username()

    if night_plan_path:
        print("Parsing the Night plan!")
        print("-------------------------------------------------------------------")
        if save_yaml_file:
            night_plan_data = parse_night_plan(night_plan_path, save_path=output_dir)
        else:
            night_plan_data = parse_night_plan(night_plan_path)
        print("Parsing complete!")
        print("-------------------------------------------------------------------")

    print("Creating the OBs!")
    print("-------------------------------------------------------------------")
    ob_creation(output_dir, night_plan_data=night_plan_data,
                res_dict=resolution_dict, manual_lst=manual_lst,
                mode_selection=mode_selection)
    print("-------------------------------------------------------------------")
    print("OB creation compete!")
    print("-------------------------------------------------------------------")

    if upload:
        print("Uploading the OBs!")
        print("-------------------------------------------------------------------")
        ob_uploader(output_dir, username=username, password=password)


if __name__ == "__main__":
    data_dir = Path("/Users/scheuck/Data/observations/")
    output_dir = Path("/Users/scheuck/Data/observations/obs")
    time_slot = data_dir / "P110" / "february_march_2023"
    night_plan_path = time_slot / "observing_plan_run7_v0.1.txt"

    # NOTE: The resolution dict
    # TODO: Make also a DIT-dictionary where ppl can change the dit of an individual thing
    # or make it possible to change either both or once at a time?
    res_dict = {"HD95881": "MED", "V1028 Cen": "MED", "HD98922": "HIGH"}

    ob_pipeline(output_dir=output_dir, night_plan_path=night_plan_path,
                save_yaml_file=False, upload=True, mode_selection="both")
