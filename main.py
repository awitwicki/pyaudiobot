import os
import pyaudio
import numpy as np
import cv2
import datetime
import wave
from telegram.ext import Updater

TELEGRAM_TOKEN = None
TELEGRAM_CHAT_ID = None

WINDOW_WIDTH = 500
WINDOW_HEIGHT = 700

#region detail settings
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

signal_level_db = 10
cutoff_freq = 200
sp = np.zeros((513, cutoff_freq), np.uint8)

recording = False
max_recording_seconds = 3
frames = []

last_record = None
last_record = datetime.datetime.now()
#endregion


#region first start
# create folders
if not os.path.exists('audio'):
    os.makedirs('audio')
    print(f"Created dir /audio")
#endregion


#region telegram
def error(update, context):
    """Log Errors caused by Updates."""
    print('Update "%s" caused error "%s"', update, context.error)

#setup telegram bot
updater: Updater = Updater(TELEGRAM_TOKEN, use_context=True)

# Get the dispatcher to register handlers
dp = updater.dispatcher
dp.add_error_handler(error)

print(f"Starting bot")

# Start the Bot
updater.start_polling()

def send_audio(file_path, duration):
    updater.bot.send_voice(
        chat_id = TELEGRAM_CHAT_ID,
        voice = open(file_path, 'rb'),
        duration = duration
        )

#endregion

#region audio
def try_delete(filename):
    try:
        print(f'removing {filename}')
        os.remove(filename)
    except Exception as e:
        print(f'e')


def create_wav(frames):
    filename = 'audio/' + datetime.datetime.now().strftime("%m%d%Y%H_%M_%S") + '.wav'
    waveFile = wave.open(filename, 'wb')
    waveFile.setnchannels(1)
    waveFile.setsampwidth(p.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()

    return filename


def convert_to_ogg(file_path):
    ogg_file_name = file_path.replace('.wav', '.ogg')
    result = os.system(f"ffmpeg -i {file_path} -c:a libvorbis -q:a 4 {ogg_file_name}")
    if result == 0:
        try_delete(file_path)
    else:
        print("Error with convertiong file")
        return file_path

    return(ogg_file_name)


def get_duration(file_path):
    duration = int(os.popen(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}').read().split('.')[0])
    return duration


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
        if val is None or val == float("-inf"):
            val = 0
        else:
            val = val / 50 * 255
        return int(val)

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

    recording_seconds = (datetime.datetime.now() - last_record).total_seconds()

    if recording:
        frames.append(data)

    if recording_seconds > max_recording_seconds:
        if recording is True:
            recording = False
            new_file = create_wav(frames)
            print(f'Saving file {new_file}')

            new_file = convert_to_ogg(new_file)
            duration = get_duration(new_file)

            send_audio(new_file, duration)
            print(f'Sending file {new_file}')

    # image transformations
    frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)
    frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))

    # put texts
    text_time = f'{round(recording_seconds, 1)} seconds'
    text_level = f'{now_value}dB/{signal_level_db}db'

    frame = cv2.putText(frame, text_time, (0, 25) , cv2.FONT_HERSHEY_SIMPLEX , 1, (0, 0, 0) , 2, cv2.LINE_AA)
    frame = cv2.putText(frame, text_level, (0, 65) , cv2.FONT_HERSHEY_SIMPLEX , 1, (0, 0, 0) , 2, cv2.LINE_AA)

    # Display the resulting frame
    cv2.imshow('spectre', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
#endregion

# When everything done, release the capture
cv2.destroyAllWindows()
