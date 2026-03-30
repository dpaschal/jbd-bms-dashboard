import argparse, time, signal, sys
from bms_monitor.simulator.simulator import BMSSimulator

SCENARIOS = ["normal", "cell-drift", "overvoltage", "overtemp", "disconnect"]


def main():
    parser = argparse.ArgumentParser(description="JBD BMS Simulator")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument("--cells", type=int, default=16, help="Number of cells (default: 16)")
    args = parser.parse_args()
    sim = BMSSimulator(scenario=args.scenario, cell_count=args.cells)
    sim.start()
    print(f"Simulator running — scenario: {args.scenario}, cells: {args.cells}")
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
