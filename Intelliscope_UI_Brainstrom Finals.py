import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import numpy as np
import os

import socket
import struct
import keyboard
import csv

import pyaudio
import pandas as pd
import wave
import tkinter as tk
from tkinter import filedialog

# Create an application instance
app = QApplication([])

# Create a plot window
app.setWindowIcon(QIcon("icon.png"))
win = pg.GraphicsLayoutWidget(show=True)
win.setWindowTitle("Intelliscope V1")

plot = win.addPlot(title="ECG - PCG Visualization")


# Set up the data buffer
data_buffer_size = 50000  # Adjust this value according to your needs
x_data = np.zeros(data_buffer_size)
y1_data = np.zeros(data_buffer_size)
y2_data = np.zeros(data_buffer_size)

ptr = 0

# Create PlotDataItems for the two graphs
curve1 = pg.PlotDataItem( pen = 'r')
curve2 = pg.PlotDataItem( pen = 'g')

# Add the PlotDataItems to the plot
plot.addItem(curve1)
plot.addItem(curve2)


HOST = '192.168.43.21'           # use the IP address of the computer running this script
PORT = 80

buffer_size = 256

# create a UDP socket and bind it to the specified port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

# receive and play the audio data
print('Program Opened')

i = 0

# Create a file writer to continuously save data to CSV
file_writer = None

# Update function for real-time plotting
def update():
    global curve1, curve2, data_buffer_size, x_data, y1_data, y2_data, ptr,i
    data, addr = sock.recvfrom((buffer_size+16) * 4)

    # convert the byte string to a NumPy array of 32-bit integers
    audio_data = np.array(struct.unpack('<' + 'i' * (buffer_size+16), data))
    
    # Receive data packet and extract x, y values
    for k in range(256):
        p = audio_data[k]
        x = i
        if p <1.88e9:
            p = 2.08e9
        y1 = p#float(audio_data[0:256])
        y2 = (audio_data[256+k//16]+1000)*1*10**6+1e9         # *1.5*10**6+1.7e9

##        if y2 <1.85e9 or y2>2.1e9:
##            y2 = 1.96e9
            
        # Append the received data to the buffer
        x_data[ptr] = x
        y1_data[ptr] = y1
        y2_data[ptr] = y2
        ptr += 1

        if file_writer is not None:
            data_to_save = np.array([x, y1, y2])
            data_to_save = data_to_save.transpose()
            file_writer.writerow(data_to_save)
            
        # If the buffer is full, roll the data to the left
        if ptr >= data_buffer_size:
            x_data[:-1] = x_data[1:]
            y1_data[:-1] = y1_data[1:]
            y2_data[:-1] = y2_data[1:]
            ptr -= 1
        i+=1
        

    # Update the plot with the new data
    curve1.setData(x_data[:ptr]/8000, y1_data[:ptr])
    curve2.setData(x_data[:ptr]/8000, y2_data[:ptr])

    

def clear_plot():
    global curve1, curve2, x_data, y1_data, y2_data, ptr
    notification_label.setText("Plot Cleared")
    curve1.clear()
    curve2.clear()
    x_data.fill(0)
    y1_data.fill(0)
    y2_data.fill(0)
    ptr = 0
    
def toggle_plot_updates():
    if timer.isActive():
        timer.stop()
        print("Plot updates disabled")
        notification_label.setText("Plotting Stopped")
    else:
        timer.start(0)
        print("Plot updates enabled")
        notification_label.setText("Plotting Started")

# Function to handle Button 2 action
def button2_action():
    print("Recorded Data deleted!")
    notification_label.setText("Recorded Data deleted!")
    # Add your custom functionality for Button 2 here

# Function to load and plot data from CSV file
def load_csv_data():
    global curve1, curve2, x_data, y1_data, y2_data, ptr
    
    print("Plotting Recorded Data")
    notification_label.setText("Plotting Recorded Data")
    
    # Open a file dialog to select the CSV file
    file_dialog = QFileDialog()
    file_path, _ = file_dialog.getOpenFileName(None, "Select CSV file", "", "CSV Files (*.csv)")

    if file_path:
        # Clear the plot before loading new data
        clear_plot()

        # Read the CSV file
        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row

            for row in reader:
                # Extract x, y1, y2 values from the row
                x, y1, y2 = map(float, row)

                # Append the data to the buffer
                x_data[ptr] = x
                y1_data[ptr] = y1
                y2_data[ptr] = y2
                ptr += 1
                curve1.setData(x_data[:ptr], y1_data[:ptr])
                curve2.setData(x_data[:ptr], y2_data[:ptr])
        
def record_data():
    global file_writer,file

    # Open a file dialog to select the output CSV file
    if file_writer is None:
        print("Recording Data")
        notification_label.setText("Recording Data")
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(None, "Save CSV file", "", "CSV Files (*.csv)")

        if file_path:
            # Create the file writer and write the header row
            file = open(file_path, 'w', newline='')
            file_writer = csv.writer(file)
            file_writer.writerow(['X', 'Y1', 'Y2'])
    else:
        print("Recording Stopped!")
        notification_label.setText("Recording Stopped!")
        # Close the file writer
        file.close()
        file_writer = None
        
def record():
    notification_label.setText("Recording Data")
    if os.path.exists("PCG.csv"):
        os.remove("PCG.csv")
        print("Filterd Deleted")
        
    while True:
        if keyboard.is_pressed("q"):
            break
        data, addr = sock.recvfrom((buffer_size+16) * 4)    
        # convert the byte string to a NumPy array of 32-bit integers
        audio_data = np.array(struct.unpack('<' + 'i' * (buffer_size+16), data))
        with open('PCG.csv', 'a') as f:
            np.savetxt(f, audio_data[0:256], delimiter=',')
    notification_label.setText("Recording Stopped!")

def convert():
    notification_label.setText("Creating Audio File")
    input_file_path = filedialog.askopenfilename(title="Select CSV file to filter")
    output_file_path = filedialog.asksaveasfilename(title="Save WAV file as", defaultextension=".wav")

    with open(input_file_path, 'r') as input_file, open("filtered.csv", 'w', newline='') as output_file:
        reader = csv.reader(input_file)
        writer = csv.writer(output_file)

        average = 2.032483648e9
        offset = 10e7
        
        next(reader)  # Skip the header row
        for row in reader:
            filtered_row = [(float(value)-(average+offset/2)) for value in row if average<=float(value) <= (average+offset)]
            writer.writerow(filtered_row)
            
    df = pd.read_csv("filtered.csv")
    audio_data = np.array(df.iloc[:, 0])
    audio_data = audio_data / np.max(np.abs(audio_data))

    with wave.open(output_file_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    if os.path.exists("filtered.csv"):
        os.remove("filtered.csv")
        print("Filterd Deleted")
    notification_label.setText("Audio File Created")

                
def create_audio():
    notification_label.setText("Creating Audio File")
    input_file_path = filedialog.askopenfilename(title="Select CSV file to filter")
    output_file_path = filedialog.asksaveasfilename(title="Save WAV file as", defaultextension=".wav")

    with open(input_file_path, 'r') as input_file, open("filtered.csv", 'w', newline='') as output_file:
        reader = csv.reader(input_file)
        writer = csv.writer(output_file)

        average = 2.032483648e9
        offset = 10e7
        
        next(reader)  # Skip the header row
        for row in reader:
            x, value, y2 = map(float, row)
            if (average) <= float(value) <= (average+offset):       
                filtered_row =  [value-(average+offset/2)] #2.08e9 <= <= 2.11e9
            else:
                continue
#                filtered_row = filtered_row
            writer.writerow(filtered_row)
            
    df = pd.read_csv("filtered.csv")
    audio_data = np.array(df.iloc[:, 0])
    audio_data = audio_data / np.max(np.abs(audio_data))

    with wave.open(output_file_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    if os.path.exists("filtered.csv"):
        os.remove("filtered.csv")
        print("Filterd Deleted")
    notification_label.setText("Audio File Created")


def play_audio():
    notification_label.setText("Playing Heart Sound")
    audio_file = filedialog.askopenfilename(title="Select Heart Sound to Play")
    
    with wave.open(audio_file, "rb") as wav_file:
        audio = pyaudio.PyAudio()
        
        def callback(in_data, frame_count, time_info, status):
            data = wav_file.readframes(frame_count)
            return (data, pyaudio.paContinue)

        stream = audio.open(format=audio.get_format_from_width(wav_file.getsampwidth()),
                            channels=wav_file.getnchannels(),
                            rate=wav_file.getframerate(),
                            output=True,
                            stream_callback=callback)

        stream.start_stream()
        while stream.is_active():
            pass

        stream.stop_stream()
        stream.close()

        audio.terminate()
    notification_label.setText("Playing Stopped!")
    
play = QIcon("icons/play.png")
erase = QIcon("icons/erase.png")
audio = QIcon("icons/audio.png")
plot = QIcon("icons/plot.jpg")
delete = QIcon("icons/delete.png")
wav = QIcon("icons/wav.png")
rec = QIcon("icons/rec.png")

# Set up a timer to periodically update the plot
timer = pg.QtCore.QTimer()
timer.timeout.connect(update)

# Create a label for notifications
Header_label = QLabel()
Header_label.setStyleSheet("color: black; font-size: 14px; background-color: white;")
Header_label.setText("INTELLISCOPE")
Header_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

notification_label = QLabel()
notification_label.setStyleSheet("color: red; font-size: 16px; background-color: white;")
notification_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

ECG_label = QLabel()
ECG_label.setStyleSheet("color: blue;")
ECG_label.setText("ECG")

PCG_label = QLabel()
PCG_label.setStyleSheet("color: red;")
PCG_label.setText("PCG")

# Create a button to toggle plot updates
toggle_button = QPushButton('Start / Stop Plotting')
toggle_button.clicked.connect(toggle_plot_updates)
toggle_button.setIcon(play)
toggle_button.setStyleSheet("text-align: left;")

# Create a button to clear the plot
clear_button = QPushButton('Erase Plot')
clear_button.clicked.connect(clear_plot)
clear_button.setIcon(erase)
clear_button.setStyleSheet("text-align: left;")

# Create Button 1
button1 = QPushButton('Plot Recorded Data')
button1.clicked.connect(load_csv_data)
button1.setIcon(plot)
button1.setStyleSheet("text-align: left;")

# Create Button 2
button2 = QPushButton('Delete Recorded Data')
button2.clicked.connect(button2_action)
button2.setIcon(delete)
button2.setStyleSheet("text-align: left;")

# Create Button 3
button3 = QPushButton('Start / Stop Recording Data While plotting')
button3.clicked.connect(record_data)
button3.setIcon(play)
button3.setStyleSheet("text-align: left;")

button4 = QPushButton('Convert PCG Data into Audio File')
button4.clicked.connect(create_audio)
button4.setIcon(audio)
button4.setStyleSheet("text-align: left;")

button5 = QPushButton('Play Recorded PCG ')
button5.clicked.connect(play_audio)
button5.setIcon(wav)
button5.setStyleSheet("text-align: left;")

button6 = QPushButton('Recorded only PCG ')
button6.clicked.connect(record)
button6.setIcon(rec)
button6.setStyleSheet("text-align: left; min-width: 150px;")

button7 = QPushButton('Only PCG to Audio ')
button7.clicked.connect(convert)
button7.setIcon(audio)
button7.setStyleSheet("text-align: left; min-width: 150px;")

# Create a layout for the widget
widget = QWidget()

Vlayout = QVBoxLayout()
H1layout = QHBoxLayout()
H2layout = QHBoxLayout()
Hlayout = QHBoxLayout()


Vlayout.addWidget(Header_label)

Vlayout.addWidget(PCG_label)
Vlayout.addWidget(ECG_label)

Vlayout.addWidget(win)
Vlayout.addWidget(notification_label)

Vlayout.addLayout(H2layout)

H2layout.addWidget(toggle_button)
H2layout.addWidget(button3)
H2layout.addWidget(button1)
H2layout.addWidget(clear_button)


Vlayout.addWidget(button4)


Vlayout.addLayout(Hlayout)

Hlayout.addWidget(button6)
Hlayout.addWidget(button7)

Vlayout.addLayout(H1layout)

H1layout.addWidget(button5)
H1layout.addWidget(button2)


# Create a widget to hold the layout

widget.setLayout(Vlayout)
widget.show()

# Start the application event loop
app.exec_()
