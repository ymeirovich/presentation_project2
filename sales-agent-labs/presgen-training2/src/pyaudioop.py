"""
Compatibility shim for the legacy `pyaudioop` module.

Some third-party audio utilities (including older versions of pydub) attempt to
import `pyaudioop`, which historically re-exported the standard library
`audioop` module.  Python 3.13 no longer bundles the optional `pyaudioop`
alias, so we provide a minimal drop-in replacement that simply forwards all
symbols from `audioop`.
"""

from audioop import *  # noqa: F401,F403 - export everything audioop provides
