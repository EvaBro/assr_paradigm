# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 17:03:18 2025

@author: Julian Bandhan, Eva Broeders

ASSR paradigm.
A pingu cartoon is played while the participant listens to an auditory clicktrain.
For good results, you either need earphones or a very good speaker. 

Before you start, verify what sound drivers you have available:
    import sounddevice as sd
    sd.query_devices()
    --> this will print the list of available sound drivers.
    
On windows, use a WASAPI driver instead of the default driver for better 
timing (lower latency between sending signal to the buffer and actual playback).
Make a note of the index of the driver of your choice, and use it to set device_index.

The script will print the estimated output latency. 

"""

import numpy as np
import sounddevice as sd
from psychopy import core, event, visual
from enum import IntFlag
import sys
from pathlib import Path
import psutil
import os

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent / 'stim_utils'))
import OptitrackUtils as opti
import ExperimentUtils as utils

# Give psychopy high scheduling priority
process = psutil.Process(os.getpid())
process.nice(psutil.HIGH_PRIORITY_CLASS)

#%% System-dependent parameters

selected_video = BASE_DIR / 'Pingu_Scooter.mp4' # Make sure the video is in the current folder or specify a file path as needed

# Select audio device
device_index = 7  # Set WASAPI as default driver for low latency. In our setuip, 7 is for MSR speaker and 10 for earphones. 
sd.default.device = device_index
device_info = sd.query_devices(sd.default.device, 'output')

print(f"Using device: {sd.query_devices(sd.default.device)['name']}")
print(f"Default Sample Rate: {device_info['default_samplerate']} Hz")

# Optimized audio settings
sample_rate = 48000  # Only supported samplerate for WASAPI
blocksize = 512  # length of audio buffer
latency_mode = 'low'

# For WASAPI, enable exclusive mode - not sure if this works for other drivers
extra_settings = sd.WasapiSettings(exclusive=True)

# Screen on which video is displayed
screen_idx=0 

framerate = 60 # Hz, system-dependent. Only used for fade at the end

# Trigger codes
class PortCodes(IntFlag):
    reset = 0       # Reset all ports
    tonetrig = 8    # Trigger for the tone
    
# Whether or not to use head motion tracking, set to False if you don't have Optitrack
optitrack = True

#%% Experiment parameters

# Parameters
intro_dur = 1            # Duration of the intro screen in seconds
end_dur = 2              # Duration of the end screen in seconds
video_dur_at_start = 5   # Let the video play for a bit before starting the sound
square_duration = 0.002  # Duration of the clicks in seconds
play_duration = 1.5      # Total duration of the square wave playback per trial
pause_duration = 1.75    # in seconds
max_jitter = 0.25        # in seconds
n_trials = 80
frequency = 40           # Hz, number of clicks per second
fade_duration = 4  # seconds, the duration of fade-out after experiment_duration is exceeded. 

#%% Audio setup

# Open an optimized output stream to check latency
with sd.OutputStream(
    device=device_index, samplerate=sample_rate,
    blocksize=blocksize, latency=latency_mode,
    extra_settings=extra_settings
) as stream:
    print(f"Reported output latency: {stream.latency:.6f} seconds")
    
#%% Generate jitters
jitters = np.random.uniform(-max_jitter, max_jitter, n_trials)
pause_durations = pause_duration + jitters
        
#%% Setup hardware, window and jitters
if optitrack:
    client = opti.setup()
    if client is not None:
        opti.set_take_name(client, 'ASSR')
        opti.start_recording(client)
else:
    client = None

# Create a window
win_size = utils.get_window_size(screen_idx) 
window = utils.create_window(win_size, screen_idx)

# Create screens
intro_screen = utils.create_staystill_screen(window)

video = visual.MovieStim(win=window, name='', autoStart=False, size=win_size, noAudio=True)
video.loadMovie(selected_video) 

#%% Tone generation

def generate_square_wave(frequency, square_duration, play_duration, sample_rate):
    period = 1/frequency

    # Number of samples for active phase, silence, and full playback
    active_samples = int(sample_rate * square_duration)
    silence_samples = int(sample_rate * (period - square_duration))
    total_samples = int(sample_rate * play_duration)

    # Generate one period: square wave + silence
    active_wave = np.ones(active_samples)
    silence_wave = np.zeros(silence_samples)
    period_wave = np.concatenate((active_wave, silence_wave))
    # Repeat the period to fill the total playback duration
    num_repeats = int(total_samples / len(period_wave))
    waveform = np.tile(period_wave, num_repeats)

    # Trim the waveform to match the exact playback duration
    waveform = 1*waveform[:total_samples]

    return waveform

# Generate the square wave
tone_data = generate_square_wave(frequency, square_duration, play_duration, sample_rate)
tone_data = tone_data.astype(np.float32)



#%% Loop

# Draw intro screen
intro_screen.draw()
window.flip()
core.wait(intro_dur)

# Play the video for a bit before starting the sound
video.play()
video_start_timer = core.CountdownTimer(video_dur_at_start)
while video_start_timer.getTime() > 0:
    video.draw()
    window.flip()
    keys = event.getKeys()
    if 'escape' in keys:
        print('Experiment aborted by user during sound.')
        sd.stop()
        utils.quit_experiment(window,client)
    if 'p' in keys:
        video.pause()
        utils.pause_experiment(window,client)
        video.play()

# Now start the actual trial loop
for trial in range(n_trials):
    print(f'Trial: {trial+1}')
       
    sd.play(tone_data, samplerate=sample_rate, device=device_index,
        blocksize=blocksize, latency=latency_mode,
        extra_settings=extra_settings) 
    
    utils.send_trigger(PortCodes.tonetrig)
    
    # Play sound
    sound_timer = core.Clock()
    while sound_timer.getTime() < play_duration:
        video.draw()
        window.flip()
        keys = event.getKeys()
        if 'escape' in keys:
            print('Experiment aborted by user during sound.')
            sd.stop()
            utils.quit_experiment(window,client)
        if 'p' in keys:
            video.pause()
            utils.pause_experiment(window,client)
            video.play()
    
    # ISI  
    sd.wait()
    pause_timer = core.CountdownTimer(pause_durations[trial])
    while pause_timer.getTime() > 0:
        video.draw()
        window.flip()
        keys = event.getKeys()
        if 'escape' in keys:
            print('Experiment aborted by user during pause.')
            sd.stop()
            utils.quit_experiment(window,client)
        if 'p' in keys:
            video.pause()
            utils.pause_experiment(window,client)
            video.play()
            
# Fade out
fade_frames = int(fade_duration * framerate)
for i in range(fade_frames):
    # Visual fade: draw video, then overlay a black rect with increasing opacity
    video.draw()
    black = visual.Rect(window, width=win_size[0], height=win_size[1], fillColor='black', opacity=i / fade_frames)
    black.draw()
    window.flip()

# End of experiment
print("Experiment complete.")
video.stop()
video.seek(0)
utils.quit_experiment(window,client)
