"""
a cool printing aid, like mediamtx's logger, for errors, warnings, etc.
"""
import datetime

dateColor = (60,60,90)

def color(text, rgb=(255,255,255)):
    return "\033[38;2;{};{};{}m{}\033[0m".format((rgb[0]), (rgb[1]), (rgb[2]), text)

def warn(string):
    date = color(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rgb=dateColor)
    war = color("WAR", rgb=(255, 255, 0))
    
    print("{} {} {}".format(date, war, string))

def error(string):
    date = color(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rgb=dateColor)
    err = color("ERR", rgb=(255, 0, 0))

    print("{} {} {}".format(date, err, string))

def info(string):
    date = color(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rgb=dateColor)
    inf = color("INF", rgb=(0, 255, 0))

    print("{} {} {}".format(date, inf, string))

def debug(string):
    date = color(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rgb=dateColor)
    inf = color("DEB", rgb=(0, 255, 0))

    print("{} {} {}".format(date, inf, string))