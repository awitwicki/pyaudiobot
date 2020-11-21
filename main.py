import pyaudio
import matplotlib.pyplot as plt
import numpy as np
import cv2

RATE = 44100
BUFFER = 1024

p = pyaudio.PyAudio()

stream = p.open(
    format = pyaudio.paFloat32,
    channels = 1,
    rate = RATE,
    input = True,
    output = False,
    frames_per_buffer = BUFFER
)

sp = np.zeros((513, 513), np.uint8)

fig = plt.figure()

def get_levels():
    try:
        data = np.fft.rfft(np.fromstring(stream.read(BUFFER), dtype=np.float32))
    except IOError:
        pass
    data = np.log10(np.sqrt(np.real(data)**2+np.imag(data)**2) / BUFFER) * 10
    return data

def translate_row(row):
    def round_int(x):
        if x == float("inf") or x == float("-inf"):
            return 255 # or x or return whatever makes sense
        return int(round(x))
    def translate_val(val):
        val=(round_int(val + 100)/100)*255
        return val

    # row = np.apply_along_axis(translate_val, -1, row)
    vals = np.array([translate_val(p) for p in row], 'uint8')
    return vals

while(True):
    # Capture frame-by-frame
    _line = get_levels()

    # translate line to 0..255 range
    line = translate_row(_line)

    # roll spectrogram
    sp = np.vstack([sp, line])
    sp = np.delete(sp, (0), axis=0)

    frame = np.array(sp)

    # max_value = round(frame.max(), 1)
    # min_value = round(frame.min(), 1)
    now_value = round(_line.max(), 1)

    frame = np.array(frame, 'uint8')

    #put texts
    text = f'{now_value}dB'
    frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)
    frame = cv2.putText(frame, text, (0, 25) , cv2.FONT_HERSHEY_SIMPLEX , 1, (0, 0, 0) , 2, cv2.LINE_AA)

    # Display the resulting frame
    cv2.imshow('spectre', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cv2.destroyAllWindows()
