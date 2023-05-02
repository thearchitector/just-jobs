from colorama import Fore, Style

from just_jobs.utils import styled_text


def test_styled_text(pcapture):
    with pcapture as target:
        with styled_text(Fore.GREEN):
            print("this should be green")

    assert target.getvalue() == Fore.GREEN + "this should be green\n" + Style.RESET_ALL
