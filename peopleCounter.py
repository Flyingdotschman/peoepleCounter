import RPi.GPIO as GPIO
import pygame
#import time

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
from sh import rm
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
loading_img = False
run_slideshow = False
stop_signal = False

# Initialisiere Pygame und zeige Vollbildmodus
pygame.init()
info_screen = pygame.display.Info()
modes = pygame.display.list_modes()

if small_window:
    win = pygame.display.set_mode((1200, 920))
else:
    win = pygame.display.set_mode(max(modes), pygame.FULLSCREEN)

pygame.display.set_caption("PeopleCounter_FGMeier")
pygame.mouse.set_visible(False)


# Schaue nach ob SD Karte vorhanden ist und mounte sie ggf
def sdcard_check():
    global sdcard_exists
    global passthrough
    global run_slideshow
    print(" Starte Checking for SD Card")
    no_sdcard_cleanup()
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
                try:
                    mount(std_dir, "/mnt/sdcard/")
                    print("SD Card Mounted")
                    prepare = threading.Thread(target=prepare_slideshow)
                    prepare.start()
                    sdcard_exists = True
                    cd("/")
                except:
                    try:
                        with open('error.txt', 'a+') as f:
                            e = sys.exc_info()[0]
                            e = strftime("%Y-%m-%d_%H_%M_%S") + " | SD_CARD_MOUNT_ERROR: " + repr(e) + "\r\n"
                            f.write(e)
                            f.flush()
                            os.fsync(f.fileno())

                    except:
                        pass

            else:
                try:
                    umount("/mnt/sdcard/")
                    std_dir = "nothing"
                    sdcard_exists = False
                    passthrough = True
                    run_slideshow = False
                    no_sdcard_cleanup()
                    print("SD Card Verloren")
                except:
                    std_dir = "nothing"
                    sdcard_exists = False
                    passthrough = True
                    no_sdcard_cleanup()
                    print("SD Card Verloren")
                    try:
                        with open('error.txt', 'a+') as f:
                            e = sys.exc_info()[0]
                            e = strftime("%Y-%m-%d_%H_%M_%S") + " | SD_CARD_UNMOUNT_ERROR: " + repr(e) + "\r\n"
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
            pass
            # Unknown file type, print a message
            #print('Skipping %s' % pathname)


def addtolist(file, extensions=['.png', '.jpg', '.jpeg', '.gif', '.bmp']):
    """Add a file to a global list of image files."""
    global file_list  # ugh
    filename, ext = os.path.splitext(file)
    e = ext.lower()
    # Only add common image types to the list.
    if e in extensions:
        print('Adding to list: ', file)
        file_list.append(file)
#else:
#print('Skipping: ', file, ' (NOT a supported image)')


# lade Bilder von SD Karte auf lokale Disk
def load_imagetodisk():
    global file_list
    print("Auf SD gefundene Bilder " + repr(len(file_list)))
    print(repr(file_list))
    for f in file_list:
        try:
            shutil.copy(f, '/home/pi/images/')
            print("Kopiere " + repr(f) + " auf Festplatte, Datei ")
        except:
            try:
                with open('error.txt', 'a+') as f:
                    e = sys.exc_info()[0]
                    e = strftime("%Y-%m-%d_%H_%M_%S") + " | IMG_TODISK_ERROR: " + repr(e) + repr(f) + "\r\n"
                    f.write(e)
                    f.flush()
                    os.fsync(f.fileno())

            except:
                pass


def do_imagelist():
    global image_list
    global modes
    files = os.listdir("/home/pi/images/")
    # files = os.path.join("/home/pi/images/", files)
    print("in images gefundene Dateien" + str(len(files)))
    # mm = pygame.display.list_modes()
    count = 0
    for _ in files:
        try:
            img = pygame.image.load(os.path.join("/home/pi/images", files[count]))
            img = img.convert()
            img = pygame.transform.rotate(img, 90)
            #            img = image_resize(img)
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
        count = count + 1
        print("Lange imagelist: " + repr(len(image_list)))


def do_diskfilelist():
    global image_list
    image_list = os.listdir("/home/pi/images/")
      

def load_image2screen(file):
    img = pygame.image.load(os.path.join("/home/pi/images/", file))
    img = img.convert()
    img = pygame.transform.rotate(img, 90)
    img = image_resize(img)
    return img


def image_resize(img):
    global info_screen

    ix, iy = img.get_size()
    if ix > iy:
        scaler = info_screen.current_w / float(ix)
        sy = scaler * iy
        if sy > info_screen.current_h:
            scaler = info_screen.current_h / float(iy)
            sx = scaler * ix
            sy = info_screen.current_h
        else:
            sx = info_screen.current_w
    else:
        scaler = info_screen.current_h / float(iy)
        sx = scaler * ix
        if sx > info_screen.current_w:
            scaler = info_screen.current_w / float(ix)
            sy = scaler * iy
            sx = info_screen.current_w
        else:
            sy = info_screen.current_h
    return pygame.transform.scale(img, (int(sx), int(sy)))


def prepare_slideshow():
    global run_slideshow
    global loading_img
    loading_img = True
    showpeoeplescreen()
    print("Loading images")
    walktree("/mnt/sdcard/", addtolist)
    load_imagetodisk()
    #do_imagelist()
    do_diskfilelist()
    run_slideshow = True
    loading_img = False
    print("done loading images")


def no_sdcard_cleanup():
    global image_list
    global file_list
    files = os.listdir("/home/pi/images/")
    for i in range(len(files)):
        try:
            rm('-r', os.path.join('/home/pi/images/', files[i]))
            print(str(i))
        except:
            try:
                with open('error.txt', 'a+') as f:
                    e = sys.exc_info()[0]
                    e = strftime("%Y-%m-%d_%H_%M_%S") + " | IMAGE_REMOVE_ERROR: " + repr(e) + repr(f) + "\r\n"
                    f.write(e)
                    f.flush()
                    os.fsync(f.fileno())

            except:
                pass
    image_list = []
    file_list = []


def slideshow():
    global run_slideshow
    global win
    global info_screen
    global FPS
    global passthrough
    global max_people
    global people_inside
    global image_list
    global loading_img
    global stop_signal

    slideshow_running = False
    image_counter = 0
    slide_show_counter = 30
    end_counter = slide_show_counter
    counter = 0
    clock = pygame.time.Clock()
    t = threading.currentThread()

    while getattr(t, "running", True):
        clock.tick(FPS)
        if not run_slideshow and slideshow_running:
            slideshow_running = False
            showpeoeplescreen()

        if run_slideshow and (counter % end_counter is 0) and len(image_list) > 0:
            passthrough = False
            slideshow_running = True
            if image_counter > (len(image_list) - 1):
                image_counter = 0
            win.fill((0, 0, 0))
            print("Loading Image: " + repr(image_list[image_counter]))
            img = load_image2screen(image_list[image_counter])
            img_rect = img.get_rect()
            img_rect.center = (int(info_screen.current_w / 2), int(info_screen.current_h / 2))

            print("DONE Loading Image: " + repr(image_list[image_counter]))
            pygame.display.flip()
            image_counter = (image_counter + 1) % len(image_list)
            counter = 1
            end_counter = slide_show_counter

            if not passthrough:
                win.blit(img, img_rect)
                pygame.display.flip()
            else:
                passthrough = False
                counter = 1

        if not stop_signal:
            counter = counter + 1


def slideshow_old():
    global run_slideshow
    global win
    global info_screen
    global FPS
    global passthrough
    global max_people
    global people_inside
    global image_list
    global loading_img

    # num_images = len(image_list)
    image_counter = 0
    slide_show_counter = 30
    druchgang_counter = 20
    end_counter = slide_show_counter
    counter = 0
    clock = pygame.time.Clock()
    t = threading.currentThread()
    stop_signal = False
    while getattr(t, "running", True):
        clock.tick(FPS)

        if loading_img:
         #   print("Laenge ImageListe: " + str(len(image_list)))
            passthrough = True
          #  print("Loading image")
        if passthrough:  # or not sdcard_exists or len(image_list) < 1:
            passthrough = False
            if people_inside >= max_people:
                stop_signal = True
                win.fill((255, 0, 0))
                text_surface, text_rect = write_text("STOP", 300, int(info_screen.current_w / 2),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                text_surface, text_rect = write_text(str(people_inside - max_people + 1) + " Personen abwarten bitte",
                                                     50,
                                                     int(info_screen.current_w / 4), int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)

            else:
                stop_signal = False
                win.fill((0, 255, 0))
                text_surface, text_rect = write_text("Herzlich", 180, int(info_screen.current_w / 8),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                text_surface, text_rect = write_text("Willkommen", 180, int(info_screen.current_w / 4),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                text_surface, text_rect = write_text("Noch", 100, int(info_screen.current_w * 2 / 5),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                text_surface, text_rect = write_text(str(max_people - people_inside), 700,
                                                     int(info_screen.current_w * 3 / 5),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                tmp = "Person"
                if (max_people - people_inside) > 1:
                    tmp = "Personen"

                text_surface, text_rect = write_text(tmp, 100,
                                                     int(info_screen.current_w * 4 / 5),
                                                     int(info_screen.current_h / 2))
                win.blit(text_surface, text_rect)
                if loading_img:
                    raduis_circle = 300
                    pygame.draw.circle(win, (255, 255, 0), (info_screen.current_w - raduis_circle * 2,
                                                            raduis_circle), raduis_circle)
                    passthrough = True
            pygame.display.flip()
            counter = 1

            end_counter = druchgang_counter
        else:
            if run_slideshow and (counter % end_counter is 0) and len(image_list) > 0:
                if image_counter > (len(image_list) - 1):
                    image_counter = 0
                win.fill((0, 0, 0))
                print("Loading Image: " + repr(image_list[image_counter]))
                img = load_image2screen(image_list[image_counter])
                #img = image_list[image_counter]
                #img = image_resize(img)
                img_rect = img.get_rect()
                img_rect.center = (int(info_screen.current_w / 2), int(info_screen.current_h / 2))
                win.blit(img, img_rect)
                print("DONE Loading Image: " + repr(image_list[image_counter]))
                pygame.display.flip()
                image_counter = (image_counter + 1) % len(image_list)
                counter = 1
                end_counter = slide_show_counter
                pygame.display.flip()
        if not stop_signal:
            counter = counter + 1


# Funtion um Text auf den Screen zu zeichnen
def write_text(text, size, x, y):
    global info_screen

    font = pygame.font.Font('freesansbold.ttf', size)
    text_surface = font.render(text, True, (255, 255, 255))
    text_surface = pygame.transform.rotate(text_surface, 90)
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
    global passthrough
    print("Einer Rein")
    people_inside = people_inside + 1
    passthrough = True
    save_reset_file()
    showpeoeplescreen()
    write_logfile("IN")


# Wird aufgerufen, wenn von den Sensoren ein gegangen Signal kommt
def peopledecrease(channel):
    global people_inside
    global passthrough
    print("Einer Raus")
    if people_inside > 0:
        people_inside = people_inside - 1
        passthrough = True
        save_reset_file()
        showpeoeplescreen()
        write_logfile("OUT")


def showpeoeplescreen():
    global people_inside
    global max_people
    global win
    global info_screen
    global stop_signal
    global passthrough

    if people_inside >= max_people:
        stop_signal = True
        win.fill((255, 0, 0))
        text_surface, text_rect = write_text("STOP", 300, int(info_screen.current_w / 2),
                                             int(info_screen.current_h / 2))
        win.blit(text_surface, text_rect)
        text_surface, text_rect = write_text(str(people_inside - max_people + 1) + " Personen abwarten bitte",
                                             50,
                                             int(info_screen.current_w / 4), int(info_screen.current_h / 2))
        win.blit(text_surface, text_rect)

    else:
        stop_signal = False
        win.fill((0, 255, 0))
        text_surface, text_rect = write_text("Herzlich", 180, int(info_screen.current_w / 8),
                                             int(info_screen.current_h / 2))
        win.blit(text_surface, text_rect)
        text_surface, text_rect = write_text("Willkommen", 180, int(info_screen.current_w / 4),
                                             int(info_screen.current_h / 2))
        win.blit(text_surface, text_rect)
        text_surface, text_rect = write_text("Noch", 100, int(info_screen.current_w * 2 / 5),
                                             int(info_screen.current_h / 2))
        win.blit(text_surface, text_rect)
        text_surface, text_rect = write_text(str(max_people - people_inside), 700,
                                             int(info_screen.current_w * 3 / 5),
                                             int(info_screen.current_h / 2))
        win.blit(text_surface, text_rect)
        tmp = "Person"
        if (max_people - people_inside) > 1:
            tmp = "Personen"

        text_surface, text_rect = write_text(tmp, 100,
                                             int(info_screen.current_w * 4 / 5),
                                             int(info_screen.current_h / 2))
        win.blit(text_surface, text_rect)
        if loading_img:
            raduis_circle = 300
            pygame.draw.circle(win, (255, 255, 0), (info_screen.current_w - raduis_circle * 2,
                                                    raduis_circle), raduis_circle)
    passthrough = True
    pygame.display.flip()




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
                print("Fehler log_datei schreiben")
        else:
            try:
                with open('/mnt/sdcard/log.txt', 'a+') as f:
                    e = "{0}, {1}, {2}, {3};\n".format(strftime("%Y-%m-%-d %H:%M:%S"), str(-1), str(people_inside),
                                                       str(max_people))
                    f.write(e)
                    f.flush()
                    os.fsync(f.fileno())

            except:
                print("Fehler log_datei schreiben")


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
    global passthrough

    print("Starte Software Jetzt !!")
    # Starte SD-Karten Thread
    sd_thread = threading.Thread(target=sdcard_check)
    sd_thread.start()
    slideshow_thread = threading.Thread(target=slideshow)
    slideshow_thread.start()
    sleep(1)

    # Lade letzten Bekannten Stand, wenn vorhanden
    max_people, people_inside = load_reset_file()
    if max_people >= people_inside:
        passthrough = True

    # Initialisiere GPIO Pins

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin_out, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(pin_in, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    GPIO.setup(pin_reset, GPIO.OUT)
    GPIO.output(pin_reset, 1)

    GPIO.add_event_detect(pin_out, GPIO.RISING, callback=peopledecrease)
    GPIO.add_event_detect(pin_in, GPIO.RISING, callback=peopleincrease)

    clock = pygame.time.Clock()
    run = True
    showpeoeplescreen()
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
            showpeoeplescreen()
        if keys[pygame.K_KP9] or keys[pygame.K_9]:
            peopleincrease(0)
        if keys[pygame.K_KP3] or keys[pygame.K_3]:
            peopledecrease(0)
        if keys[pygame.K_KP7] or keys[pygame.K_7]:
            max_people = max_people + 1
            showpeoeplescreen()
        if keys[pygame.K_KP1] or keys[pygame.K_1]:
            max_people = max_people - 1
            showpeoeplescreen()

    sd_thread.running = False
    slideshow_thread.running = False
    sd_thread.join()
    slideshow_thread.join()
    pygame.quit()
    GPIO.cleanup()


if __name__ == '__main__':
    main()
