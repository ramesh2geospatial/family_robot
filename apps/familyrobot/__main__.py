"""
Entrypoint command-line interface for FamilyRobot.
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="FamilyRobot - Low-cost, local-first companion."
    )
    parser.add_argument(
        "--platform",
        choices=["desktop", "android", "raspberrypi"],
        help="Force execution platform (otherwise auto-detected from environment).",
    )
    parser.add_argument(
        "--config",
        help="Path to custom configuration YAML file.",
    )

    args = parser.parse_args()

    print("FamilyRobot CLI initialized successfully.")
    print(f"Platform: {args.platform or 'auto-detect'}")
    print(f"Config path: {args.config or 'default'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
