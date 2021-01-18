import pyaudio
import numpy as np
import cv2
import datetime
import wave

RATE = 44100
BUFFER = 1024
FORMAT = pyaudio.paInt16

p = pyaudio.PyAudio()


stream = p.open(
    format = FORMAT,
    channels = 1,
    rate = RATE,
    input = True,
    output = False,
    frames_per_buffer = BUFFER
)

IS_PLAY_ONLY = True

signal_level_db = 10
cutoff_freq = 200
sp = np.zeros((513, cutoff_freq), np.uint8)

recording = False
max_recording_seconds = 3
frames = []

last_record = None
last_record = datetime.datetime.now()


def get_data():
    data = stream.read(BUFFER)
    return data

def get_levels(data_in):
    try:
        data = np.fft.rfft(np.fromstring(data_in, dtype=np.int16))
    except IOError:
        pass
    data = np.log10(np.sqrt(np.real(data)**2+np.imag(data)**2) / BUFFER) * 10
    return data

def translate_row(row):
    def translate_val(val):
        try:
            if val is None:
                val = 0
            else:
                val = val / 50 * 255
            return int(val)
        except:
            print(val)

    vals = np.array([translate_val(p) for p in row], 'uint8')
    return vals

while(True):
    # Capture frame-by-frame
    data = get_data()
    _line = get_levels(data)

    # translate line to 0..255 range
    line = translate_row(_line)

    #cutoff_frequency
    line = line[:cutoff_freq]

    # roll spectrogram
    sp = np.vstack([sp, line])
    sp = np.delete(sp, (0), axis=0)

    frame = np.array(sp)

    now_value = round(np.average(_line), 1)

    #record
    if now_value > signal_level_db:
        last_record = datetime.datetime.now()

        if recording is False:
            recording = True

    frame = np.array(frame, 'uint8')

    #put texts
    recording_seconds = (datetime.datetime.now() - last_record).total_seconds()
    text = f'{recording_seconds} seconds'

    if recording:
        frames.append(data)

    if recording_seconds > max_recording_seconds:
        if recording is True:
            filename = datetime.datetime.now().strftime("%m%d%Y%H_%M_%S") + '.wav'
            waveFile = wave.open(filename, 'wb')
            waveFile.setnchannels(1)
            waveFile.setsampwidth(p.get_sample_size(FORMAT))
            waveFile.setframerate(RATE)
            waveFile.writeframes(b''.join(frames))
            waveFile.close()
            recording = False

    # text = f'{now_value}dB'
    frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)
    frame = cv2.putText(frame, text, (0, 25) , cv2.FONT_HERSHEY_SIMPLEX , 1, (0, 0, 0) , 2, cv2.LINE_AA)

    # Display the resulting frame
    cv2.imshow('spectre', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cv2.destroyAllWindows()
