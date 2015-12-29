from pyspark import SparkContext
from util import *
import audio
import graphic
import output
import scipy.io.wavfile as wav
import sys

def read_wav(f):
  samplerate, signal = wav.read(f)
  #if len(signal.shape) > 1:
  #  signal = signal[:,0]
  return (f, signal, samplerate)

def apply_melfilter(f, signal, samplerate):
  filterbank_energies = audio.melfilterbank.logfilter(samplerate, signal, winlen=0.00833, winstep=0.00833, nfilt=39, lowfreq=0, preemph=1.0)
  #print f, samplerate, filterbank_energies.shape
  return (f, filterbank_energies)

def generate_spectrograms(f, signal, samplerate):
  Sxx = audio.spectrogram.spectrogram_cutoff(samplerate, signal)
  return (f, Sxx)

def sliding_audio(f, signal, samplerate):
  for window_name, window in audio.windowing.sliding_with_filename(f, signal, samplerate, 5, 5, 0.6):
    yield (window_name, window, samplerate)

def main(args):
  window_size = 600
  files = filecollector.collect(args.input_path)

  sc = SparkContext("local", "sparkline")
  pipeline = (
    sc.parallelize(files, 4)
    .map(lambda f: read_wav(f))
    .map(lambda (f, signal, samplerate): (filename.truncate_extension(f), signal, samplerate))
    .flatMap(lambda (f, signal, samplerate): sliding_audio(f, signal, samplerate))
    .map(lambda (f, signal, samplerate): generate_spectrograms(f, signal, samplerate))
    #.map(lambda (f, signal, samplerate): apply_melfilter(f, signal, samplerate))
    .map(lambda (f, image): (f, graphic.colormapping.to_grayscale(image, bytes=True)))
    #.flatMap(lambda (f, image): list(graphic.windowing.sliding_with_filenames(f, image, window_size, window_size, 0.6)))
    .map(lambda (f, image): (f, graphic.histeq.histeq(image)))
    .map(lambda (f, image): (f, graphic.windowing.cut_or_pad_window(image, window_size)))
    .map(lambda (f, image): output.image.save(f, image, args.output_path))
  )
  
  pipeline.collect()


if __name__ == '__main__':

  args = argparser.parse()
  main(args)