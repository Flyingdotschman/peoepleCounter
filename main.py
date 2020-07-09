import peopleCounter
import sys
import os
from time import strftime

def main():
    try:
        peopleCounter.main()
    except:
        try:
            with open('error.txt', 'a+') as f:
                e = sys.exc_info()[0]
                e = strftime("%Y-%m-%d_%H_%M_%S")+" | MAIN_ERROR: " + repr(e) + "\r\n"
                f.write(e)
                f.flush()
                os.fsync(f.fileno())

        except:
            pass


if __name__ == '__main__':
    main()
