"""Main program :)"""
from .main import main
import sys

# Do we need the if __name__ == '__main__' guard here?
# https://stackoverflow.com/questions/61417426/is-if-name-main-required-in-a-main-py

if __name__ == '__main__':
    main(sys.argv[1:])
