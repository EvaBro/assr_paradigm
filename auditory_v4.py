# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 17:03:18 2025

@author: Julian Bandhan, Eva Broeders
"""

import numpy as np
import sounddevice as sd
from psychopy import core, parallel, event, visual
from enum import IntFlag
from utils import stim

import os
os.chdir(os.path.dirname(os.path.abspath(__file__))) 

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

selected_video = 'Pingu_Scooter.mp4'#'pingu_season1_trim.mp4'

#%% Audio setings

# Select audio device
device_index = 7  # Set WASAPI as default driver for low latency. 7 for MSR speaker and 10 for earphones
sd.default.device = device_index
device_info = sd.query_devices(sd.default.device, 'output')

print(f"Using device: {sd.query_devices(sd.default.device)['name']}")
print(f"Default Sample Rate: {device_info['default_samplerate']} Hz")

# Optimized audio settings
sample_rate = 48000  # Only supported samplerate for WASAPI
blocksize = 512  # length of audio buffer
latency_mode = 'low'

# For WASAPI, enable exclusive mode 
extra_settings = sd.WasapiSettings(exclusive=True)
    
# Open an optimized output stream to check latency
with sd.OutputStream(
    device=device_index, samplerate=sample_rate,
    blocksize=blocksize, latency=latency_mode,
    extra_settings=extra_settings
) as stream:
    print(f"Reported output latency: {stream.latency:.6f} seconds")
    
# Generate jitters
jitters = np.random.uniform(-max_jitter, max_jitter, n_trials)
pause_durations = pause_duration + jitters
    
#%% Trigger Settings
trigger_port_address = 0xcFF8  # Address for parallel port (modify as needed)

# Initialize parallel port for triggers
trig_port = parallel.ParallelPort(trigger_port_address)

# Trigger codes
class PortCodes(IntFlag):
    reset = 0       # Reset all ports
    tonetrig = 8    # Trigger for the tone
    

#%% Video Settings

# Screen on which video is displayed
screen_idx=0 # Should be 0 for stim PC

# Create a window
win_size = stim.get_window_size(screen_idx)
window = stim.create_window(win_size, screen_idx)

# Use this instead of previous line if you want pingu to play on the left screen
# So another video can be played simultaneously on the right
# Without a psychopy window, this script will not work
# window = visual.Window(size = (800, 600), screen = 1, fullscr = False) 

# Create screens
intro_screen = stim.create_staystill_screen(window)
end_screen = stim.create_end_screen(window)

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

video.play()

# Play the video for a bit before starting the sound
video_start_timer = core.CountdownTimer(video_dur_at_start)
while video_start_timer.getTime() > 0:
    video.draw()
    window.flip()
    if 'escape' in event.getKeys():
        print('Experiment aborted by user during sound.')
        sd.stop()
        window.close()
        core.quit()


for trial in range(n_trials):
    print(f'Trial: {trial+1}')
       
    sd.play(tone_data, samplerate=sample_rate, device=device_index,
        blocksize=blocksize, latency=latency_mode,
        extra_settings=extra_settings) 
    
    trig_port.setData(PortCodes.tonetrig)
    core.wait(0.005)
    trig_port.setData(0)
    
    # Create trial timer (sound duration)
    sound_timer = core.Clock()
    while sound_timer.getTime() < play_duration:
        # Keep updating the video
        if not video.isFinished:
            video.draw()
            window.flip()
        else:
            window.flip()  # Still need to flip to handle keyboard
        if 'escape' in event.getKeys():
            print('Experiment aborted by user during sound.')
            sd.stop()
            window.close()
            core.quit()
    
    # Wait for tone duration  
    sd.wait()

    pause_timer = core.CountdownTimer(pause_durations[trial])
    while pause_timer.getTime() > 0:
        if not video.isFinished:
            video.draw()
            window.flip()
        else:
            window.flip()
        if 'escape' in event.getKeys():
            print('Experiment aborted by user during pause.')
            sd.stop()
            window.close()
            core.quit()

end_screen.draw()
window.flip()
core.wait(end_dur)

# End of experiment
print("Experiment complete.")
window.close()
core.quit()
