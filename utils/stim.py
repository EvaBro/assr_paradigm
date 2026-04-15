# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 11:54:18 2024

@author: Eva Broeders

"""
from psychopy import visual, core, parallel, event
import os
import pyglet
from utils.ParallelButtonBox import ButtonBox

# Trigger settings
trig_port = parallel.ParallelPort(0xcFF8)
trigger_time = 0.001

# Buttonbox settings
btn_box = ButtonBox(address=0xdff8)


def create_img_list(img_path, dur=0):
    if dur == 0:
        img_files = [img_path + img for img in os.listdir(img_path) if img.endswith(('.bmp','.png'))]
    else:    
        img_files = [(img_path + img, dur) for img in os.listdir(img_path) if img.endswith(('.bmp','.png', '.BMP'))]
    return img_files

def create_staystill_screen(window):
    intro_screen = visual.TextStim(win=window, text="Please stay very still.", color='white',
                                   height=0.15, alignText='center', anchorHoriz='center',
                                   anchorVert='center')
    return intro_screen

def create_end_screen(window):
    end_screen = visual.TextStim(win=window, text="Thank you for watching!", color='white',
                                   height=0.15, alignText='center', anchorHoriz='center',
                                   anchorVert='center')
    return end_screen

def create_fixation_screen(window):
    fixation = visual.TextStim(win=window, text='+', color='white',
                            height=0.1, alignText='center', anchorHoriz='center',
                            anchorVert='center')
    return fixation

def get_window_size(screen_idx):
    display = pyglet.canvas.get_display()
    screens = display.get_screens()
    primary_screen = screens[screen_idx]  # Use the primary screen (or adjust index for others)
    win_size = primary_screen.width, primary_screen.height
    return win_size

def create_window(win_size, screen_idx):
    window = visual.Window(fullscr=True, size=win_size, screen=screen_idx, monitor="testMonitor", color="black", checkTiming=False)
    return window

def scale_imgs(images, scale_w, scale_h):
    for img in images:
        img_w = img.size[0]*scale_w
        img_h = img.size[1]*scale_h
        img.size = (img_w, img_h)
        
def send_trigger(code):
    trig_port.setData(code)
    core.wait(trigger_time)
    trig_port.setData(0)
    
def check_button_press_continuous(PortCodes, clock, window, img_end_time):
    # Reset
    btn_pressed = False
    
    while not btn_pressed and img_playing(clock, img_end_time):
        keys = event.getKeys()
        jsbtns = btn_box.getAllButtons()[1:3]
        if any(jsbtns):
            print(jsbtns)
            send_trigger(PortCodes.button)  #sends a trigger that button is pressed
            btn_pressed = True            
            
        elif 'escape' in keys:
            window.close()
            core.quit()

            
    return btn_pressed

def check_button_press(PortCodes):
    btn_pressed = False
    jsbtns = btn_box.getAllButtons()[1:3]
    if any(jsbtns):
         print(jsbtns)
         send_trigger(PortCodes.button)  #sends a trigger that button is pressed
         btn_pressed = True        
    return btn_pressed
        
def img_playing(clock, img_end_time):
    current_time = clock.getTime()
    if current_time < img_end_time:
        return True
    else:
        return False
    

    