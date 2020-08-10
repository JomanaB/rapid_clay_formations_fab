"""Fabrication runner for Rapid Clay Fabrication project for fullscale structure.

Run from command line using :code:`python -m compas_rcf.abb.run`
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging as log
import pathlib
import sys
import time
from datetime import datetime
from operator import attrgetter
from pathlib import Path

import questionary
from compas_fab.backends.ros import RosClient
from compas_rrc import PrintText

from compas_rcf import __version__
from compas_rcf.abb import DOCKER_COMPOSE_PATHS
from compas_rcf.abb import ROBOT_IPS
from compas_rcf.abb import AbbRcfClient
from compas_rcf.docker import compose_up
from compas_rcf.fab_data import ABB_RCF_CONF_TEMPLATE
from compas_rcf.fab_data import ClayBulletEncoder
from compas_rcf.fab_data import PickStation
from compas_rcf.fab_data import fab_conf
from compas_rcf.fab_data import load_bullets

# This reduces latency, see:
# https://github.com/gramaziokohler/roslibpy/issues/41#issuecomment-607218439
from twisted.internet import reactor  # noqa: E402 isort:skip

reactor.timeout = lambda: 0.0001


def logging_setup():
    """Configure logging for module and imported modules."""
    loglevel_dict = {0: log.WARNING, 1: log.INFO, 2: log.DEBUG}

    timestamp_file = datetime.now().strftime("%Y%m%d-%H.%M.%S.log")
    log_file = Path(log_dir) / timestamp_file

    log.basicConfig(
        level=loglevel_dict[args.verbose],
        format="%(asctime)s:%(levelname)s:%(funcName)s:%(message)s",
        handlers=[log.FileHandler(log_file, mode="a"), log.StreamHandler(sys.stdout)],
    )


def setup_fab_data(clay_bullets):
    """Check for placed bullets in JSON.

    Parameters
    ----------
    clay_bullets : list of :class:`compas_rcf.fabrication.clay_objs.ClayBullet`
        Original list of ClayBullets.

    Returns
    -------
    list of :class:`compas_rcf.fabrication.clay_objs.ClayBullet`
        Curated list of ClayBullets
    """
    maybe_placed = [bullet for bullet in clay_bullets if bullet.placed is not None]

    if len(maybe_placed) < 1:
        return clay_bullets

    last_placed = max(maybe_placed, key=attrgetter("bullet_id"))
    last_placed_index = clay_bullets.index(last_placed)

    log.info(
        "Last bullet placed was {:03}/{:03} with id {}.".format(
            last_placed_index, len(clay_bullets), last_placed.bullet_id
        )
    )

    skip_options = questionary.select(
        "Some or all bullet seems to have been placed already.",
        [
            "Skip all bullet marked as placed in JSON file.",
            "Place all anyways.",
            questionary.Separator(),
            "Place some of the bullets.",
        ],
    ).ask()

    if skip_options == "Skip all bullet marked as placed in JSON file.":
        to_place = [bullet for bullet in clay_bullets if bullet not in maybe_placed]
    if skip_options == "Place all anyways.":
        to_place = clay_bullets[:]
    if skip_options == "Place some of the bullets.":
        skip_method = questionary.select(
            "Select method:",
            ["Place last N bullets again.", "Pick bullets to place again."],
        ).ask()
        if skip_method == "Place last N bullets again.":
            n_place_again = questionary.text(
                "Number of bullets from last to place again?",
                "1",
                lambda val: val.isdigit() and -1 < int(val) < last_placed_index,
            ).ask()
            to_place = clay_bullets[last_placed_index - int(n_place_again) + 1 :]
            log.info(
                "Placing last {} bullets again. First bullet will be id {}.".format(
                    n_place_again, to_place[0].bullet_id,
                )
            )
        else:
            to_place_selection = questionary.checkbox(
                "Select bullets:",
                [
                    "{:03} (id {}), marked placed: {}".format(
                        i, bullet.bullet_id, bullet.placed is not None
                    )
                    for i, bullet in enumerate(clay_bullets)
                ],
            ).ask()
            indices = [int(bullet.split()[0]) for bullet in to_place_selection]
            to_place = [clay_bullets[i] for i in indices]

    return to_place


################################################################################
# Script runner                                                                #
################################################################################
def main(run_conf):
    """Fabrication runner, sets conf, reads json input and runs fabrication process."""
    ############################################################################
    # Docker setup                                                            #
    ############################################################################
    ip = {"ROBOT_IP": ROBOT_IPS[run_conf.robot_client.controller]}
    compose_up(DOCKER_COMPOSE_PATHS["driver"], check_output=True, env_vars=ip)
    log.debug("Driver services are running.")

    ############################################################################
    # Load fabrication data                                                    #
    ############################################################################
    clay_bullets = load_bullets(run_conf.fab_data)
    log.info("Fabrication data read from: {}".format(run_conf.fab_data))

    log.info("{} items in clay_bullets.".format(len(clay_bullets)))

    # Integrate into AbbRcfClient?
    with run_conf.pick_conf.open(mode="r") as fp:
        pick_station = PickStation.from_data(json.load(fp))

    ############################################################################
    # setup in_progress JSON                                                   #
    ############################################################################
    json_progress_identifier = "-IN_PROGRESS"

    if run_conf.fab_data.stem.endswith(
        json_progress_identifier
    ) or run_conf.fab_data.stem.endswith(json_progress_identifier + ".log"):
        progress_file = run_conf.fab_data
    else:
        progress_file = run_conf.fab_data.with_name(
            run_conf.fab_data.stem + json_progress_identifier + run_conf.fab_data.suffix
        )

    i = 1
    while progress_file.exists():
        progress_file = progress_file / ".{:02}".format(i)

    done_file = progress_file.with_name(
        str(progress_file.name).replace(json_progress_identifier, "-DONE")
    )

    # Create Ros Client                                                        #
    with RosClient() as ros:

        # Create AbbRcf client (subclass of AbbClient)
        rob_client = AbbRcfClient(ros, run_conf.robot_client)

        rob_client.check_reconnect()

        ############################################################################
        # Fabrication loop                                                         #
        ############################################################################

        to_place = setup_fab_data(clay_bullets)

        if not questionary.confirm("Ready to start program?").ask():
            log.critical("Program exited because user didn't confirm start.")
            print("Exiting.")
            sys.exit()

        # Set speed, accel, tool, wobj and move to start pos
        rob_client.pre_procedure()

        for bullet in to_place:
            bullet.placed = None
            bullet.cycle_time = None

        for i, bullet in enumerate(to_place):
            current_bullet_desc = "Bullet {:03}/{:03} with id {}.".format(
                i, len(to_place) - 1, bullet.bullet_id
            )

            rob_client.send(PrintText(current_bullet_desc))
            log.info(current_bullet_desc)

            pick_frame = pick_station.get_next_frame(bullet)

            # Pick bullet
            pick_future = rob_client.pick_bullet(pick_frame)

            # Place bullet
            place_future = rob_client.place_bullet(bullet)

            bullet.placed = 1  # set placed to temporary value to mark it as "placed"

            # Write progress to json while waiting for robot
            with progress_file.open(mode="w") as fp:
                json.dump(clay_bullets, fp, cls=ClayBulletEncoder)
            log.debug("Wrote clay_bullets to {}".format(progress_file.name))

            # This blocks until cycle is finished
            cycle_time = pick_future.result() + place_future.result()

            bullet.cycle_time = cycle_time
            log.debug("Cycle time was {}".format(bullet.cycle_time))
            bullet.placed = time.time()
            log.debug("Time placed was {}".format(bullet.placed))

        ############################################################################
        # Shutdown procedure                                                       #
        ############################################################################

        # Write progress of last run of loop
        with progress_file.open(mode="w") as fp:
            json.dump(clay_bullets, fp, cls=ClayBulletEncoder)
        log.debug("Wrote clay_bullets to {}".format(progress_file.name))

        if len([bullet for bullet in clay_bullets if bullet.placed is None]) == 0:
            progress_file.rename(done_file)
            log.debug("Saved placed bullets to {}.".format(done_file))

        rob_client.post_procedure()


if __name__ == "__main__":
    """Entry point, logging setup and argument handling."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "run_data_file", type=pathlib.Path, help="File containing fabrication setup.",
    )
    parser.add_argument(
        "-d",
        "--dist-sensor",
        action="store",
        dest="tools.dist_sensor.serial_port",
        help="Specify port distance sensor is connected on. E.g. COM4",
    )
    parser.add_argument(
        "-c",
        "--controller",
        choices=["real", "virtual"],
        default="virtual",
        dest="robot_client.controller",
        help="Set fabrication runner target.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Set log level. -v adds INFO messages and -vv adds DEBUG messages.",
    )
    args = parser.parse_args()

    # Load dictionary from file specified on command line
    with args.run_data_file.open(mode="r") as f:
        run_data = json.load(f)

    log_dir = run_data["log_dir"]

    # Read config-default.yml for default values
    fab_conf.read(user=False, defaults=True)

    if run_data.get("log_dir"):
        fab_conf["log_dir"] = run_data["log_dir"]
    logging_setup()

    # Import options from argparse
    fab_conf.set_args(args, dots=True)

    # Read conf file specified in run_data
    log.info("Configuration loaded from {}".format(run_data["conf_path"]))
    fab_conf.set_file(run_data["conf_path"])

    # Add paths from run_data to fab_conf
    fab_conf["fab_data"] = run_data["fab_data_path"]
    fab_conf["pick_conf"] = run_data["pick_conf_path"]

    # Validate conf
    run_conf = fab_conf.get(ABB_RCF_CONF_TEMPLATE)

    log.info("compas_rcf version: {}".format(__version__))
    log.info("Using {} controller.".format(run_conf.robot_client.controller))
    log.debug("argparse input: {}".format(args))
    log.debug("config after set_args: {}".format(fab_conf))

    main(run_conf)
