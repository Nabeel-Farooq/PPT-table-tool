import ctypes
import datetime
import json
import os
import select
import subprocess
import sys
import time

from pathlib import Path
from typing import Any, Optional, Tuple


IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    import msvcrt


class Utils:
    """
    General utility helper class.
    """

    def __init__(
        self,
        name: str = "Python Script",
    ):
        self.name = name

        self.colors_dict = self._load_colors()

    # ==================================================
    # INTERNAL HELPERS
    # ==================================================

    def _load_colors(self) -> dict:
        """
        Load colors.json if it exists.
        """

        colors_path = (
            Path(__file__).resolve().parent
            / "colors.json"
        )

        if not colors_path.exists():
            return {}

        try:
            with colors_path.open(
                encoding="utf-8"
            ) as file:
                return json.load(file)

        except Exception:
            return {}

    # ==================================================
    # ADMIN / PRIVILEGES
    # ==================================================

    def check_admin(self) -> bool:
        """
        Check whether the current process
        is running with administrator privileges.
        """

        try:
            return os.getuid() == 0

        except AttributeError:
            return (
                ctypes.windll.shell32
                .IsUserAnAdmin() != 0
            )

    def elevate(
        self,
        file_path: str,
    ) -> None:
        """
        Relaunch script with administrator privileges.
        """

        if self.check_admin():
            return

        if IS_WINDOWS:

            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                f'"{file_path}"',
                None,
                1,
            )

            return

        try:
            process = subprocess.Popen(
                ["which", "sudo"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout, _ = process.communicate()

            sudo_path = stdout.decode(
                "utf-8",
                "ignore",
            ).strip()

            os.execv(
                sudo_path,
                [
                    "sudo",
                    sys.executable,
                    *sys.argv,
                ],
            )

        except Exception:
            sys.exit(1)

    # ==================================================
    # VERSION HELPERS
    # ==================================================

    def compare_versions(
        self,
        version1: str,
        version2: str,
        *,
        separator: str = ".",
        pad: str = "0",
        ignore_case: bool = True,
    ) -> Optional[bool]:
        """
        Compare two version strings.

        Returns:
            True:
                version1 < version2

            False:
                version1 > version2

            None:
                versions are equal
        """

        version1 = str(version1)
        version2 = str(version2)

        if ignore_case:
            version1 = version1.lower()
            version2 = version2.lower()

        parts1, parts2 = self.pad_length(
            version1.split(separator),
            version2.split(separator),
            pad=pad,
        )

        for part1, part2 in zip(parts1, parts2):

            clean1 = "".join(
                char for char in part1
                if char.isalnum()
            )

            clean2 = "".join(
                char for char in part2
                if char.isalnum()
            )

            clean1, clean2 = self.pad_length(
                clean1,
                clean2,
                pad=pad,
            )

            if clean1 < clean2:
                return True

            if clean1 > clean2:
                return False

        return None

    def pad_length(
        self,
        value1: Any,
        value2: Any,
        *,
        pad: str = "0",
    ) -> Tuple[Any, Any]:
        """
        Pad two values to equal length.
        """

        pad = str(pad)[0]

        if type(value1) is not type(value2):
            return value1, value2

        length_difference = len(value1) - len(value2)

        if length_difference < 0:

            missing = abs(length_difference)

            if isinstance(value1, list):
                value1.extend([pad] * missing)

            else:
                value1 = (
                    pad * missing
                ) + value1

        elif length_difference > 0:

            if isinstance(value2, list):
                value2.extend(
                    [pad] * length_difference
                )

            else:
                value2 = (
                    pad * length_difference
                ) + value2

        return value1, value2

    # ==================================================
    # PATH HELPERS
    # ==================================================

    def check_path(
        self,
        path: str,
    ) -> Optional[str]:
        """
        Attempt to sanitize and validate a path.
        """

        test_path = path.strip()

        while test_path:

            if os.path.exists(test_path):
                return os.path.abspath(test_path)

            # Remove surrounding quotes
            if (
                len(test_path) >= 2
                and test_path[0] == test_path[-1]
                and test_path[0] in ('"', "'")
            ):
                test_path = test_path[1:-1]
                continue

            # Expand user path
            expanded = os.path.expanduser(
                test_path
            )

            if expanded != test_path:
                test_path = expanded
                continue

            # Handle escaped slashes
            fixed = "\\".join(
                part.replace("\\", "")
                for part in test_path.split("\\\\")
            )

            if fixed == test_path:
                break

            test_path = fixed

        return None

    # ==================================================
    # INPUT HELPERS
    # ==================================================

    def grab(
        self,
        prompt: str,
        *,
        timeout: int = 0,
        default: Any = None,
    ) -> Any:
        """
        Prompt user for input with optional timeout.
        """

        if timeout <= 0:
            return input(prompt)

        sys.stdout.write(prompt)
        sys.stdout.flush()

        user_input = ""

        if IS_WINDOWS:

            start_time = time.time()

            while True:

                if msvcrt.kbhit():

                    char = msvcrt.getche()

                    if ord(char) == 13:
                        break

                    if ord(char) >= 32:
                        user_input += char.decode(
                            errors="ignore"
                        )

                if (
                    not user_input
                    and (
                        time.time() - start_time
                    ) > timeout
                ):
                    break

        else:

            readable, _, _ = select.select(
                [sys.stdin],
                [],
                [],
                timeout,
            )

            if readable:
                user_input = (
                    sys.stdin.readline()
                    .strip()
                )

        print()

        return (
            user_input
            if user_input
            else default
        )

    # ==================================================
    # TERMINAL HELPERS
    # ==================================================

    @staticmethod
    def cls() -> None:
        """
        Clear terminal screen.
        """

        os.system(
            "cls"
            if IS_WINDOWS
            else "clear"
        )

    def cprint(
        self,
        message: str,
        *,
        strip_colors: bool = False,
    ) -> Optional[str]:
        """
        Print colored terminal text.
        """

        if IS_WINDOWS:
            strip_colors = True

        reset = "\u001b[0m"

        colors = getattr(
            self,
            "colors",
            [],
        )

        for color in colors:

            if strip_colors:
                message = message.replace(
                    color["find"],
                    "",
                )

            else:
                message = message.replace(
                    color["find"],
                    color["replace"],
                )

        if strip_colors:
            return message

        sys.stdout.write(message)
        print(reset)

        return None

    def head(
        self,
        text: Optional[str] = None,
        width: int = 55,
    ) -> None:
        """
        Draw terminal header.
        """

        self.cls()

        title = text or self.name

        print("-" * width)

        middle_padding = max(
            (width - len(title) - 2) // 2,
            0,
        )

        middle = (
            "|"
            + (" " * middle_padding)
            + title
            + (
                " "
                * (
                    width
                    - middle_padding
                    - len(title)
                    - 2
                )
            )
            + "|"
        )

        if len(middle) > width:
            middle = middle[: width - 4] + "...|"

        print(middle)
        print("-" * width)

    @staticmethod
    def resize(
        width: int,
        height: int,
    ) -> None:
        """
        Resize terminal window.
        """

        print(
            f"\033[8;{height};{width}t"
        )

    # ==================================================
    # EXIT
    # ==================================================

    def custom_quit(self) -> None:
        """
        Display exit message and terminate.
        """

        self.head()

        print("by Anton Sychev\n")
        print(
            "https://github.com/klich3/PPT-table-tool\n"
        )

        print(
            "Thanks for testing it out.\n"
        )

        print(
            "Created for the community, "
            "by the community.\n"
        )

        print(
            "Collaborated with Perez987\n"
        )

        print(
            "https://github.com/perez987/"
            "6600XT-on-macOS-with-"
            "PowerPlayTable-on-SSDT-or-config.plist\n"
        )

        current_hour = (
            datetime.datetime.now()
            .time()
            .hour
        )

        if 4 <= current_hour < 12:
            message = "Have a nice morning!"

        elif 12 <= current_hour < 17:
            message = "Have a nice afternoon!"

        elif 17 <= current_hour < 21:
            message = "Have a nice evening!"

        else:
            message = "Have a nice night!"

        print(f"{message}\n")

        sys.exit(0)
