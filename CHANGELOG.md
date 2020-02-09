# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

### Changed

### Removed


## \[0.1.9\] \[2020-02-09\]

### Added

- Print colored dict function added to `compas_rcf.utils.ui`.
- Packages Colorama and Questionary added to to requirements. They are used for CLI runner.

### Changed

- `compas_rcf.fabrication.abb_fabrication_non_interactive` refactored
- `compas_rcf.fabrication.abb_fabrication_non_interactive` renamed to `abb_rcf_runner`.
- `compas_rcf.fabrication.abb_rcf_runner` now takes args and can edit conf setup during runtime.
- `compas.rcf.fabrication.ClayBullet` property `placement_frame` changed to be where the tool should stop while placing. New property `location` is the new required argument for the object and defines the clay bullets lowest point. `placement_frame` is derived from `location` and `compressed height`.
- `ClayBulley` attributes `pre_frames` and `post_frames` renamed to `trajectory_to` and `trajectory_from` to be more descriptive.
- Fixes to docs: In Updating section of `getting_started.rst` python was changed to pip. Inline comments removed from
    installation instructions.

## \[0.1.8\] \[2020-02-07\]

### Changed

- After some testing to find the best way to distribute this package given the dependency on private repository `compas_rrc` I've concluded to keep uploading to PyPi. This means that compas\_rrc will need to be installed manually before this package, since PyPi does not allow giving a \"direct dependency\`.

## \[0.1.6\] 2020-02-06

### Added

- Set up sphinx docs
- Added deploy job for travis
- Open file dialog function added to new module `compas_rcf.util.ui`
- Open file dialog implemented in ABB fabrication runner

### Changed

- Travis Python 3 version bumped up to 3.7
- docs moved from docsource to docs
- sphinx target directory now dist/docs
- Corrected compas\_fab version range (from `<0.12` to `<0.11`)
- Fixed compas\_rrc requirement syntax given it's installed from git repository
- Added compas\_rrc to installable packages for `compas_rcf.install_rhino`

## \[0.1.5\] 2020-02-05

### Added

- `ClayBulletEncoder` to serialize `ClayBullet` added to `compas_rcf.fabrication.clay_obj`
- Frames before and after placement added to `ClayBullet`
- `from_data` constructor added to `ClayBullet`
- Function to parse list of ClayBullet instances from JSON added in new module `compas_rcf.utils.json_`
- `ensure_frame` function added to `compas_rcf.utils.util_funcs` to convert `Planes` to `Frames`
- `compas_rcf.IPY` global boolean that uses `compas` function to check if IronPython is running the code.

### Changed

- `Rhino` modules are only loaded if IronPython is running the code
- `compas_rcf.fabrication.abb_fabrication_non_interactive` now reads JSON to load ClayBullets and extracts `Frames` from them
- Most settings in `abb_fabrication_non_interactive` are moved to top and set as globals.

### Removed

- `compas_rcf.utils.databases` mock module removed in favor of `json_`.

## \[0.1.4\] 2020-02-05

### Added

- Added abb non-interactive fabrication script
- Added docker-compose files for ABB ROS setup

## \[0.1.3\] 2020-02-04

### Added

- Example file `grasshopper_non_interactive` setup in docs
- Partly finished structure for future ur online fabrication procedure

### Changed

- `utils.py` now divided into multiple modules
- Other renames and moves

### Removed

## \[0.1.2\] 2020-02-03

### Changed

- Name change from `rcf` to `compas_rcf`.

## \[0.1.1\] 2020-02-03

### Added

- First release, package setup by applying [compas-dev/cookiecutter-pypackage](https://github.com/compas-dev/cookiecutter-pypackage) on small library of modules from previous phase of project

### Changed

- `rcf/ur` renamed to `rcf/ur_control`
- Fabrication related functions moved from `rcf/ur` to `rcf/fabrication`

### Removed

- Unused code in `rcf/ur_control`

## \[0.1.0\]

- Start value for version