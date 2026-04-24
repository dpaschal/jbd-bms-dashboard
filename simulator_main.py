import argparse, time, signal, sys
from bms_monitor.simulator.simulator import BMSSimulator, CHEMISTRY

SCENARIOS = ["normal", "cell-drift", "overvoltage", "overtemp", "disconnect"]

PRESETS = {
    # Matt's rig — 4S LiFePO4 prismatic, 302Ah (confirmed from real BMS).
    "matt": {
        "cells": 4, "chemistry": "lifepo4", "ah": 302.0,
        "soc": 69, "temps": 3,
    },
    # Small 4S LiFePO4 generic test pack.
    "4s-lifepo4": {
        "cells": 4, "chemistry": "lifepo4", "ah": 100.0,
        "soc": 85, "temps": 3,
    },
    # Generic 4S Li-ion 18650 bench pack.
    "4s-18650": {
        "cells": 4, "chemistry": "li-ion", "ah": 3.0,
        "soc": 85, "temps": 3,
    },
    # Larger 16S LiFePO4 pack for stress testing the cells widget.
    "16s-lifepo4": {
        "cells": 16, "chemistry": "lifepo4", "ah": 100.0,
        "soc": 83, "temps": 2,
    },
}


def main():
    parser = argparse.ArgumentParser(description="JBD BMS Simulator")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument("--preset", choices=list(PRESETS), default="matt",
                        help="Pack preset (default: matt — 4S LiFePO4 310Ah)")
    parser.add_argument("--cells", type=int, help="Override cell count")
    parser.add_argument("--chemistry", choices=list(CHEMISTRY),
                        help="Override chemistry")
    parser.add_argument("--ah", type=float, help="Override nominal Ah")
    parser.add_argument("--soc", type=int, help="Override initial SOC%%")
    parser.add_argument("--temps", type=int, help="Override temp sensor count (max 4)")
    args = parser.parse_args()

    preset = dict(PRESETS[args.preset])
    if args.cells is not None:     preset["cells"] = args.cells
    if args.chemistry is not None: preset["chemistry"] = args.chemistry
    if args.ah is not None:        preset["ah"] = args.ah
    if args.soc is not None:       preset["soc"] = args.soc
    if args.temps is not None:     preset["temps"] = args.temps

    sim = BMSSimulator(
        scenario=args.scenario,
        cell_count=preset["cells"],
        chemistry=preset["chemistry"],
        nominal_ah=preset["ah"],
        initial_soc=preset["soc"],
        temp_count=preset["temps"],
    )
    sim.start()
    chem = CHEMISTRY[preset["chemistry"]]
    pack_v = chem["nominal"] * preset["cells"]
    print(f"Simulator — scenario={args.scenario} preset={args.preset}")
    print(f"  {preset['cells']}S {preset['chemistry']} {preset['ah']}Ah, "
          f"~{pack_v:.1f}V nominal, SOC={preset['soc']}%, {preset['temps']} temps")
    print(f"Connect the app to: {sim.app_port}")
    print("Press Ctrl+C to stop.")

    def _stop(sig, frame):
        print("\nStopping simulator…")
        sim.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
