"""
SWITCH INVENTORY SCRIPT

Script will conduct audit info extraction from switch devices.
It requires a ``config.json`` file. If script is running first time, template will be created in a script directory.
Script logs its actions into ``/logs`` subdirectory created, by default, in a script location - can be adjusted.

IMPORTANT!

- before running this script, provide credentials in a ``[config.json]`` file,
- provide list of IP addresses, as a comma-delimited list of strings in a ``[config.json]`` file,
per device type as suggested in a config template created on a script first run,
- ensure script is running with enough privileges as to create mentioned config and log files.

"""

# import libraries
import csv
import time
import json
import logging
from typing import Any
from pathlib import Path
from datetime import datetime
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException


def main() -> None:
    """
    Execute main script functions.
    Check for a config file if it is present within script directory, create one as a template if not present.
    Check for a switches IP list file as well before any action is taken.
    Proceed if all criteria are met.
    """
    # create log object
    log = check_for_log()
    log.info("new script instance running")
    # config file check and import (if possible)
    _config = check_for_configuration(log)
    # perform actions if previous actions successful
    data = execute_data_requests(log, _config)
    # perform export
    export_data(log, data)


# ---------------------------------
# files check function
# ---------------------------------
def check_for_log() -> logging.Logger:
    """
    Create a log file in a script location subdirectory.
    Return logger object configured for a local file and a console output.
    Exit script execution in case of an exception.

    :return: log object
    :rtype: logging.Logger
    :raise Exception: ``exc`` log file / directory creation exception, exiting script as a result
    """
    # log parameters
    log_name = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_switch_inventory_report.log"
    try:
        # adjust target logs directory as needed - by default: subdirectory in a script location
        log_directory = Path(__file__).parent / 'logs'
        log_directory.mkdir(exist_ok=True)
        log_path = log_directory / log_name
        # create logger
        logger = logging.getLogger(log_name)
        logger.setLevel(logging.INFO)
        # file handler setting
        if not logger.handlers:
            file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                                        datefmt='%Y-%m-%d %H:%M:%S'))
            logger.addHandler(file_handler)
        # console output handler setting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                                       datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(console_handler)
        return logger
    except Exception as exc:
        print(f"cannot create local log object: {str(exc)}; script will now exit")
        exit()


def check_for_configuration(log: logging.Logger) -> dict[str, Any]:
    """
    Perform config check in a script directory, return its content if found. Create empty config file if not present.
    If a config file has just been created - provide a prompt to fill it with credentials.
    Exit script execution in case of an exception.

    :param log: log object
    :type log: logging.getLogger()
    :return: config file content, optional
    :rtype: dict[str, Any]
    :raise Exception: ``exc`` config file check / creation issue
    """
    # define path
    config_path = Path(__file__).parent / "config.json"
    # check for a file, create one if not present
    # exit on exception or if config has just been created and require providing details.
    try:
        if not config_path.exists():
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(get_file_template(), f, indent=4)
            log.info(f"[config.json] not present, created a new one in a script directory"
                     f" - provide required details within a file then run script again.")
            exit()
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)
            log.info(f"[config.json] content imported successfully")
        # return if both data collected
        # data volume will be validated as a next step of script execution, ending the script if no credentials or
        # devices info has been provided
        return imported_data
    except Exception as exc:
        log.critical(f"cannot perform script config check: {str(exc)}. Script will now exit.")
        exit()


def get_file_template() -> dict[str, Any]:
    """
    Store empty default file templates for use with a script. Return template when requested to create a file.

    :return: json file structure dictionary
    :rtype: dict[str, Any]
    """
    # default config file structure
    # IMPORTANT: specify IP addresses of devices matching switch type
    # IMPORTANT: switch types can be configured freely
    return {'username': '',
            'password': '',
            'devices': {'Cisco-IOS': ['192.168.1.1', '192.168.1.2']}
            }


# ---------------------------------
# main script activities
# ---------------------------------
def execute_data_requests(log: logging.Logger, _config: dict[str, Any]) -> dict[str, Any] | None:
    """
    Per each device from switches list execute software upgrade actions.

    :param log: log object
    :param _config: configuration file content dict
    :type log: logging.Logger
    :type: _config: dict[str, Any]
    :return: device data, optional
    :rtype: dict[str, Any] or None
    :raise Exception: ``exc`` config data retrieval issue, check `config.json` file content
    """
    data = {}
    # obtain credentials from config
    try:
        log.info(f"reading data from [config.json]")
        _username = _config['username']
        _password = _config['password']
        _devices = _config['devices']
    except Exception as exc:
        log.critical(f"cannot read data from [config.json], check file structure. Exception: {str(exc)}")
        exit()

    # validate credentials
    if not _username and not _password:
        log.warning(f"credentials not provided, script will now exit.")
        exit()

    # proceed with execution of commands per devices as grouped by OS version in a [switches.json] file
    for device_type in _devices:
        # prepare default data header
        # this will be used for each exported file, grouped by a device type
        results = [['IP', 'SN', 'Model', 'Port', 'PortStatus']]
        for device in _devices[device_type]:
            log.info(f"-------------------")
            log.info(f"DEVICE IP: {device}")
            # create device details dictionary for connection setting
            # this will be used with netmiko library connection handler
            _json = {"device_type": device_type, "host": device, "username": _username, "password": _password}
            # process connection, return obtained data
            _details = get_switch_details(log, _json)
            if _details:
                results.extend(_details)
            else:
                log.warning(f"no device info obtained, skipping")
                continue
        # validate data volume, append to dict
        if len(results) > 1:
            data[device_type] = results
    # final data validation:
    return data if data else None


def get_switch_details(log: logging.Logger, _json: dict[str, Any]) -> list[Any] | None:
    """
    Main function responsible for obtaining device details via a connection with a device.

    :param log: log object
    :param _json: request details dict
    :type log: logging.Logger
    :type _json: dic[str, str]
    :return: specific device details list, optional
    :rtype: list[str] or None
    :raise Exception: ``exc`` version data retrieval from device failed, check command execution chain
    :raise Exception: ``exd`` interfaces data retrieval from device failed, check command execution chain
    :raise Exception: ``exe`` unspecified netmiko exception: please debug communication chain
    :raise Exception: ``exf`` unspecified ports info parsing exception: please debug script results for a device
    """
    serial_number = None
    interfaces = None
    ports = []
    # attempt to obtain data
    # anticipate general netmiko connection exceptions
    try:
        with ConnectHandler(**_json) as net_connect:
            # firstly attempt to obtain device serial number and model
            try:
                version_info = net_connect.send_command("show version")
                serial_number = get_version_detail(log, version_info, 'serial')
                device_model = get_version_detail(log, version_info, 'model')
            except Exception as exc:
                log.warning(f"> cannot obtain serial number: {str(exc)}")
            # secondly, attempt to obtain network interfaces response
            # these records will be parsed to provide port details
            try:
                interfaces = net_connect.send_command("show interfaces status", use_textfsm=True)
                #print(interfaces)
            except Exception as exd:
                log.warning(f"> cannot obtain interfaces output: {str(exd)}")

        # finally, if obtained interfaces info, parse those to get basic port status data
        # append device serial number and model info as well
        if interfaces:
            for interface in interfaces:
                port_name = interface['port']
                port_status = interface['status']
                ports.append([port_name, port_status])

    # manage possible exceptions
    except NetMikoTimeoutException:
        log.warning(f"> connection timed out")
        return None
    except NetMikoAuthenticationException:
        log.warning(f"> authentication failed, please re-check credentials")
        return None
    except Exception as exe:
        log.warning(f"> unspecified exception: {str(exe)}")
        return None

    # return results if operations successful
    if not ports:
        log.warning("no ports info obtained")
        return None
    try:
        results = [[_json['host'], serial_number, device_model, port[0], port[1]] for port in ports]
        log.info("device details obtained")
        time.sleep(5)
        return results
    except Exception as exf:
        log.warning(f"exception while formatting device port data: {str(exf)}")
        return None


def get_version_detail(log: logging.Logger, version_info: str, detail: str) -> str:
    """
    Utility function to parse device detail from obtained version info object.

    :param log: log object
    :param str version_info: device version info object
    :param str detail: version detail indicator: serial or model
    :type log: logging.getLogger()
    :return: requested parameter string
    :rtype: str
    :raise Exception: ``exc`` string parsing issue, check parsed output and parsed function to validate proper
            data extraction from versions output content
    """
    info = None
    try:
        # attempt to obtain serial number from a specific text record
        if detail == 'serial':
            for line in version_info.splitlines():
                if "System Serial Number" in line or "System serial" in line:  # changed "System serial number"
                    info = line.split()[-1]
        # attempt to obtain device model info from a specific text record
        if detail == 'model':
            for line in version_info.splitlines():
                if "cisco" in line.lower() and ("processor" in line.lower() or "chassis" in line.lower()):
                    parts = line.split()
                    if len(parts) >= 2:
                        info = parts[1]
    # anticipate any exception
    except Exception as exc:
        log.warning(f"Unspecified exception while attempting to obtain {detail} from device version info: {str(exc)}")
        return 'No data'
    # handle missing data
    # parsing may need to be adjusted to reflect searching pattern more closely
    if not info:
        log.warning(f"> no {detail} info found within obtained version info: {str(version_info)}. Validate parsing in"
                    f"[get_version_detail] function if adjusted incorrectly")
        return 'No data'
    else:
        log.info(f"> device {detail}: {info}")
        return info


# ---------------------------------
# data export
# ---------------------------------
def export_data(log: logging.Logger, data: dict[str, Any]) -> None:
    """
    Export data function, saving device info in *.csv format. Files are being dumped in a script directory.

    :param log: log object
    :param data: devices data dict
    :type log: logging.Logger
    :type data: dict[str, Any]
    :raise Exception: ``exc`` data export exception - please check if file can be exported to a designated
            directory and, optionally, validate exported content
    """
    log.info("-------------------")
    if data:
        log.info(f"attempting data export: {len(data)} data set(s)")
        try:
            # set file save parameters
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            export_directory = Path(__file__).parent / 'exports'
            export_directory.mkdir(exist_ok=True)
            # export files per subject
            for subject in data:
                export_name = f"{timestamp}_{subject}_export.csv"
                export_path = export_directory / export_name
                # perform export
                with open(export_path, "w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerows(data[subject])
                log.info(f"> file saved: {export_path}")
        # exit script on any potential exception
        except Exception as exc:
            log.warning(f"cannot perform data export: {str(exc)}, script will now exit")
        exit()
    else:
        log.info("no data to export")
    log.info("all actions finished")
    return


if __name__ == '__main__':
    main()
