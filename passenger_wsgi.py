import sys, os
INTERP = os.getenv('APP_INTERPRETER')
if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

from feedfuser import app as application

# the kind of hackery required to get Passenger to use a virtualenv Python installation