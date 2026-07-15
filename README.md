# SIMMBA: Smart Infrastructure Mapping, Modular Base and Algorithms

SIMMBA is a modular mobile sensing platform for transportation-infrastructure mapping research. This repository contains the platform's existing sensor-acquisition software and desktop interface, preserved from the project codebase on which SIMMBA is based.

> **Project status:** Research software under active development. Validate sensor configuration, timing, calibration, and data quality before field deployment or engineering use.

## Project Overview

SIMMBA supports coordinated collection of positioning and inertial measurements for mobile transportation-infrastructure surveys. The current software provides command-line and graphical acquisition paths, sensor-specific interfaces, live status display, and optional recording of observations to CSV files. This repository is intended to accompany SIMMBA publications and provide a stable, citable software record.

## Motivation

Transportation researchers require repeatable ways to collect spatially referenced observations of roadway and active-transportation assets. A modular platform allows instruments to be selected for a study, replaced as needs evolve, and operated through a common acquisition workflow.

## Key Features

- Simultaneous GNSS and IMU acquisition through independent processes.
- Adapters for u-blox GNSS receivers, MicroStrain IMUs, and WitMotion IMUs.
- PySide6 desktop interface for sensor selection, monitoring, and recording.
- Serial-device discovery and a Bluetooth interface implemented in the GUI.
- Optional NTRIP client configuration for supported GNSS workflows.
- Timestamped CSV recording and live display of decoded observations.
- Linux-oriented helpers for GPSD, PTP, and network-interface setup.

Availability depends on the instrument, operating system, and configuration. This repository does not include a general-purpose map-generation algorithm.

## System Architecture

```text
GNSS receiver(s) ---> sensor adapter ---\
                                          +--> acquisition processes --> display
IMU sensor(s) -----> sensor adapter ---/                          \--> CSV records

Optional services: NTRIP corrections | GPSD | PTP/network setup
Interfaces:         command line | PySide6 desktop GUI
Downstream:         study-specific quality control and map generation
```

Sensor adapters decode observations and place records on queues. The command-line and GUI layers coordinate acquisition, display current values, and optionally persist data.

## Hardware Platform

The checked-in software contains interfaces for:

- u-blox-based GNSS receivers, including Pro and sensor-fusion selections exposed by the software;
- MicroStrain 3DM-CV7-AHRS IMUs;
- WitMotion IMUs supported by the included serial parser; and
- Ethernet-connected equipment operated through external vendor software where configured.

The repository does not prescribe a bill of materials, wiring, mounting, or calibration procedure. Consult the project team and device manufacturers before reproducing a field system.

## Software Platform

- `code/`: command-line acquisition and Linux setup scripts.
- `gui/`: PySide6 desktop application with serial, Bluetooth, and NTRIP-related components.

The scripts use Linux system services and utilities. The GUI's existing instructions specify Python 3.10 and dependencies in `gui/requirements.txt`.

## Data Acquisition Workflow

1. Mount and cable instruments according to the approved field protocol.
2. Confirm ports, baud rates, time settings, recording location, and storage.
3. Start the command-line path or GUI and connect only the deployed instruments.
4. Enable recording when required and monitor sensor status.
5. Stop acquisition cleanly, preserve original files, and document anomalies.
6. Perform project-specific quality assurance before analysis.

## Map Generation Workflow

Map generation is not implemented as a standalone pipeline here. A typical downstream research workflow is to preserve raw CSV output and metadata; verify timestamps, coordinates, status, and completeness; apply the publication's documented synchronization, calibration, filtering, georeferencing, and quality-control methods; generate mapped products in the study-specific analysis environment; and archive parameters and provenance. This outline is not an implemented capability.

## Repository Structure

```text
.
|-- code/                 # Command-line acquisition and Linux helpers
|-- gui/                  # PySide6 acquisition application
|   |-- assets/           # Existing application images
|   |-- src/              # GUI, sensor, serial, and utility modules
|   `-- vendor/           # Existing vendored MSCL Python package
|-- paper/                # Publication placeholder and citation guidance
|-- README.md             # Project documentation
|-- CITATION.cff          # GitHub citation metadata
|-- CONTRIBUTING.md       # Contribution guidance
|-- CODE_OF_CONDUCT.md    # Community expectations
`-- CHANGELOG.md          # Documentation-level change record
```

## Installation

No universal procedure has been validated for every hardware configuration. For the GUI, the existing project instructions specify Python 3.10, a virtual environment, the dependencies in `gui/requirements.txt`, and `pysidedeploy.spec` for deployment.

After creating and activating a Python 3.10 environment:

```bash
cd gui
python -m pip install -r requirements.txt
python main.py
```

Some paths require Linux utilities, device permissions, vendor libraries, or hardware. Review `gui/INSTRUCTIONS.md`, `code/init.sh`, and `code/start.sh` first. Those scripts may install packages or change system, network, time, and service configuration.

## Basic Usage

Inspect command-line options without connecting a sensor:

```bash
cd code
python main.py --help
```

The command accepts explicit sensor port and baud-rate pairs plus optional `--save` and `--path` arguments. Use values established for the deployed hardware. For GUI operation, start `gui/main.py`, configure the recording folder and instruments, then connect and terminate acquisition through the interface.

## Applications

- Mobile surveys of roadway and active-transportation infrastructure.
- Spatially referenced transportation-asset observations.
- Evaluation of modular GNSS/IMU field configurations.
- Research datasets for condition-assessment and mapping studies.
- Reproducible transportation-engineering field experiments.

Derived measurements and conclusions depend on study design, calibration, processing, and validation—not on acquisition software alone.

## Citation

Coming Soon

## Contact Information

Contact the **Centre for Smart Transportation** through its [GitHub organization](https://github.com/CENTRE-FOR-SMART-TRANSPORTATION).
