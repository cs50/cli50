import os
from pkg_resources import DistributionNotFound, get_distribution

# https://stackoverflow.com/a/17638236/5156190
try:

    # Get package's distribution
    _dist = get_distribution("cli50")

    # Normalize path for cross-OS compatibility
    _dist_loc = os.path.normcase(_dist.location)
    _here = os.path.normcase(__file__)

    # This version is not installed, but another version is
    if not _here.startswith(os.path.join(_dist_loc, "cli50")):
        raise DistributionNotFound

except DistributionNotFound:
    __version__ = "locally installed, version not available"

else:
    __version__ = _dist.version
