import RPi.GPIO as GPIO
import pygame
import time

from time import strftime
from time import sleep
import pickle
import threading
import shutil
import os
import sys
from sh import mount
from sh import umount
from sh import cd
import stat

# Konfig
small_window = True
FPS = 10

pin_out = 20
pin_in = 16
pin_reset = 12

waittime = 20

# Laufzeit Variablen
sdcard_exists = False
max_people = 20
people_inside = 0

file_list = []
image_list = []

passthrough = False

# Initialisiere Pygame und zeige Vollbildmodus
pygame.init()
info_screen = pygame.display.Info()

if small_window:
    win = pygame.display.set_mode((1200, 920))
else:
    modes = pygame.display.list_modes()
    win = pygame.display.set_mode(max(modes))

pygame.display.set_caption("PeopleCounter_FGMeier")
pygame.mouse.set_visible(False)


# Schaue nach ob SD Karte vorhanden ist und mounte sie ggf
def sdcard_check():
    global sdcard_exists
    " Starte Checking for SD Card"
    sdcard_exists = os.path.ismount("/mnt/sdcard/")
    std_dir = "nothing"
    t = threading.currentThread()
    while getattr(t, "running", True):
        if not sdcard_exists:
            for f in os.listdir("/dev/"):
                if "mmc" in f and "0" not in f and "p1" in f:
                    std_dir = "/dev/" + f
                    print("SD Card gefunden")
        if os.path.exists(std_dir) ^ sdcard_exists:
            if not sdcard_exists:
                mount(std_dir, "/mnt/sdcard/")
                print("SD Card Mounted")
                prepare = threading.Thread(target=prepare_slideshow)
                prepare.start()
                # sdcard_exists = True
                cd("/")

            else:
                try:
                    umount("/mnt/sdcard/")
                    sdcard_exists = False
                    no_sdcard_cleanup()
                    print("SD Card Verloren")
                except:
                    try:
                        with open('error.txt', 'a+') as f:
                            e = sys.exc_info()[0]
                            e = strftime("%Y-%m-%d_%H_%M_%S") + " | IMG_LOAD_ERROR: " + repr(e) + "\r\n"
                            f.write(e)
                            f.flush()
                            os.fsync(f.fileno())

                    except:
                        pass
        sleep(1)


def walktree(top, callback):
    """recursively descend the directory tree rooted at top, calling the
    callback function for each regular file. Taken from the module-stat
    example at: http://docs.python.org/lib/module-stat.html
    """
    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        mode = os.stat(pathname)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            # It's a directory, recurse into it
            walktree(pathname, callback)
        elif stat.S_ISREG(mode):
            # It's a file, call the callback function
            callback(pathname)
        else:
            # Unknown file type, print a message
            print('Skipping %s' % pathname)


def addtolist(file, extensions=['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
    """Add a file to a global list of image files."""
    global file_list  # ugh
    filename, ext = os.path.splitext(file)
    e = ext.lower()
    # Only add common image types to the list.
    if e in extensions:
        print('Adding to list: ', file)
        file_list.append(file)
    else:
        print('Skipping: ', file, ' (NOT a supported image)')


# lade Bilder von SD Karte auf lokale Disk
def load_imagetodisk():
    global file_list
    for f in file_list:
        try:
            shutil.copy(f, '/home/pi/images/')
        except:
            try:
                with open('error.txt', 'a+') as f:
                    e = sys.exc_info()[0]
                    e = strftime("%Y-%m-%d_%H_%M_%S") + " | IMG_TODISK_ERROR: " + repr(e) + "\r\n"
                    f.write(e)
                    f.flush()
                    os.fsync(f.fileno())

            except:
                pass


def do_imagelist():
    files = os.listdir("/home/pi/images/")
    mm = pygame.display.list_modes()

    for current in files:
        try:
            img = pygame.image.load(files[current])
            img = img.convert()
            img = pygame.transform.rotate(img, 90)
            img = pygame.transform.scale(img, max(modes))
            image_list.append(img)
        except pygame.error as err:
            try:
                with open('error.txt', 'a+') as f:
                    e = strftime("%Y-%m-%d_%H_%M_%S") + " | IMG_TOLIST_ERROR: " + repr(err) + "\r\n"
                    f.write(e)
                    f.flush()
                    os.fsync(f.fileno())

            except:
                pass


def prepare_slideshow():
    global sdcard_exists

    walktree("/mnt/sdcard/", addtolist)
    load_imagetodisk()
    do_imagelist()
    sdcard_exists = True


'''   t=threading.Thread(target=slideshow)
t.start()'''


def no_sdcard_cleanup():
    global image_list
    global file_list
    image_list = []
    file_list = []


def slideshow():
    global sdcard_exists
    global win
    global info_screen
    global FPS
    global passthrough
    global max_people
    global people_inside
    global image_list

    num_images = len(image_list)
    image_counter = 0
    slide_show_counter = 200
    druchgang_counter = 20
    end_counter = slide_show_counter
    counter = slide_show_counter
    clock = pygame.time.Clock()
    t = threading.currentThread()
    stop_signal = False
    while getattr(t, "running", True):
        clock.tick(FPS)
        if passthrough:
            if people_inside > max_people:
                stop_signal = True
                win.fill(255, 0, 0)
                text_surface, text_rect = write_text("STOP", 300, int(info_screen.current_w/2),
                                                     int(info_screen.current_h/2))
                win.blit(text_surface, text_rect)
                text_surface, text_rect = write_text(str(people_inside-max_people+1)+" Personen abwarten bitte", 50,
                                                     int(info_screen.current_w / 4), int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)

            else:
                stop_signal = False
                win.fill(0, 255, 0)
                text_surface, text_rect = write_text("Herzlich", 180, int(info_screen.current_w / 8),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                text_surface, text_rect = write_text("Willkommen", 180, int(info_screen.current_w / 4),
                                                     int(info_screen.current_h / 2))
                text_surface, text_rect = write_text("Noch", 100, int(info_screen.current_w * 2 / 5),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                text_surface, text_rect = write_text(str(max_people - people_inside), 700,
                                                     int(info_screen.current_w * 3 / 5),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                tmp = "Person"
                if (max_people - people_inside) > 1:
                    tpm = "Personen"

                text_surface, text_rect = write_text(tmp, 100,
                                                     int(info_screen.current_w * 4 / 5),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)

            pygame.display.flip()
            counter = 0
            end_counter = druchgang_counter
        else:
            if sdcard_exists and (counter % end_counter is 0):
                win.blit(image_list[image_counter], 0, 0)
                pygame.display.flip()
                image_counter = (image_counter + 1) % num_images
                counter = 0
                end_counter = slide_show_counter
        if not stop_signal:
            counter = counter + 1


# Funtion um Text auf den Screen zu zeichnen
def write_text(text, size, x, y):
    global info_screen

    font = pygame.font.Font('freesansbold.ttf', size)
    text_surface = font.render(text, True, (255, 255, 255))
    text_surface = pygame.transfrom.rotate(text_surface, 90)
    text_w, text_h = text_surface.get_size()
    ratio = (float(text_w) / float(text_h))
    if text_h > info_screen.current_h * 0.9:
        text_surface = pygame.transform.smoothscale(text_surface, (
            int(info_screen.current_h * 0.9 * ratio), int(info_screen.current_h * 0.9)))
    text_rect = text_surface.get_rect()
    text_rect.center = (x, y)
    return text_surface, text_rect


# Lade reset File, um den letzten bekannten Stand zu holen
def load_reset_file():
    try:
        with open("/home/pi/reset/save.pkl", "r") as f:
            mp, pi = pickle.load(f)
            if mp is None:
                mp = 20
            if pi is None:
                pi = 0
    except:
        mp = 20
        pi = 0
    return mp, pi


# Speichere Reset File bzw den aktuellen Stand der Personen im Laden
def save_reset_file():
    global max_people
    global people_inside
    with open("/home/pi/reset/save.pkl", "w+") as f:
        pickle.dump([max_people, people_inside], f)


# Wird aufgerufen, wenn von den Sensoren ein eingetroffen Signal kommt
def peopleincrease(channel):
    global people_inside
    people_inside = people_inside + 1
    write_logfile("IN")


# Wird aufgerufen, wenn von den Sensoren ein gegangen Signal kommt
def peopledecrease(channel):
    global people_inside
    if people_inside > 0:
        people_inside = people_inside - 1
    write_logfile("OUT")


def write_logfile(name):
    global sdcard_exists
    global people_inside
    global max_people

    if sdcard_exists:
        if name is "IN":
            try:
                with open('/mnt/sdcard/log.txt', 'a+') as f:
                    e = "{0}, {1}, {2}, {3};\n".format(strftime("%Y-%m-%-d %H:%M:%S"), str(+1), str(people_inside),
                                                       str(max_people))
                    f.write(e)
                    f.flush()
                    os.fsync(f.fileno())

            except:
                pass
        else:
            try:
                with open('/mnt/sdcard/log.txt', 'a+') as f:
                    e = "{0}, {1}, {2}, {3};\n".format(strftime("%Y-%m-%-d %H:%M:%S"), str(-1), str(people_inside),
                                                       str(max_people))
                    f.write(e)
                    f.flush()
                    os.fsync(f.fileno())

            except:
                pass


def arduino_reset():
    global pin_reset
    GPIO.output(pin_reset, 0)
    sleep(0.1)
    GPIO.output(pin_reset, 1)


# Hier Startet das eigentliche Programm
def main():
    global sdcard_exists
    global small_window
    global max_people
    global people_inside
    global pin_in
    global pin_out
    global pin_reset
    global FPS

    print("Starte Software Jetzt !!")
    # Starte SD-Karten Thread
    sd_thread = threading.Thread(target=sdcard_check)
    sd_thread.start()
    slideshow_thread = threading.Thread(target=slideshow)
    slideshow_thread.start()
    sleep(1)

    # Lade letzten Bekannten Stand, wenn vorhanden
    max_people, people_inside = load_reset_file()

    # Initialisiere GPIO Pins

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin_out, GPIO.IN, pull_down=GPIO.PUD_DOWN)
    GPIO.setup(pin_in, GPIO.IN, pull_down=GPIO.PUD_DOWN)

    GPIO.setup(pin_reset, GPIO.OUT)
    GPIO.output(pin_reset, 1)

    GPIO.add_event_detect(pin_out, GPIO.RISING, callback=peopledecrease)
    GPIO.add_event_detect(pin_in, GPIO.RISING, callback=peopleincrease)

    clock = pygame.time.Clock()
    run = True
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type is pygame.QUIT:
                run = False
        keys = pygame.key.get_pressed()

        if keys[pygame.K_q]:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        if keys[pygame.K_KP5] or keys[pygame.K_5]:
            people_inside = 0

        if keys[pygame.K_KP7] or keys[pygame.K_7]:
            peopleincrease(0)
        if keys[pygame.K_KP1] or keys[pygame.K_1]:
            peopledecrease(0)
    pygame.quit()
    sd_thread.running = False
    slideshow_thread.running = False
    GPIO.cleanup()
