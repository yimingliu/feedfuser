import sys, os
INTERP = "/home/serrana/.pyenvs/feedfuser/bin/python"
if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

from feedfuser import app as application

# the kind of hackery required to get Passenger to use a virtualenv Python installation