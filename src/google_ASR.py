import io
import os
import logging
import sys
import argparse
import time
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Imports the Google Cloud client library
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types

def main():
    parser = argparse.ArgumentParser("Script for google ASR, [python3 .py google_credentials list]")
    parser.add_argument("--repeat", default=3,type=int)
    parser.add_argument("--googleLicense",required=True, type=str)
    parser.add_argument("--inputList",required=True, type=str)
    args = parser.parse_args()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = args.googleLicense#sys.argv[1]#"My Project.json"
    
    logging.basicConfig(level=logging.INFO,  
                    filename=args.inputList+'.log',  
                    filemode='a',  
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')  

    # Instantiates a client
    client = speech.SpeechClient()
    filelist = args.inputList#sys.argv[2]#'dry-run-1_map_pcm.txt'
    # The name of the audio file to transcribe
    googleresultdict = {}
    logging.info('=============')
    logging.info('CREDENTIALS'+args.googleLicense)
    print('CREDENTIALS'+args.googleLicense)
    try:
        repeatnum = args.repeat#args.repeat
    except Exception as e:
        repeatnum = 3
    with open(filelist,'r',encoding='utf8') as f:
        for line in f.readlines():
            file_name = line.strip().split('\t')[0]
            try:
                hint = line.strip().split('\t')[1].split(',')
            except:
                hint = ''
            config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='zh-TW',
            speech_contexts=[speech.types.SpeechContext(phrases=hint,)]
            )
            print(file_name)
            print(hint)
            logging.info('process'+file_name)
            logging.info('hint:'+','.join(hint))
            # Loads the audio into memory
            with io.open(file_name, 'rb') as audio_file:
                content = audio_file.read()
                audio = types.RecognitionAudio(content=content)
            response = ''
            # Detects speech in the audio file
            
            for i in range(repeatnum):
                try:
                    response = client.recognize(config, audio)
                except Exception as e:
                    eprint(e,'\ntry',str(i),'/',str(repeatnum),'sleep 1 sec')
                    time.sleep(1)
                if not response == '':
                    break
                
            googleresult = ''
            confidence = ''
            if response == '':
                googleresultdict[file_name] = ''+'\t'+''
            else:
                for result in response.results:
                    try:
                        googleresult = result.alternatives[0].transcript
                    except Exception as e:
                        logging.warning(e)
                        googleresult = ''
                    try:
                        confidence = result.alternatives[0].confidence
                    except Exception as e:
                        logging.warning(e)
                        confidence = ''
                    break
                googleresultdict[file_name] = googleresult+'\t'+str(confidence)
            
    with open(filelist+'.google','w',encoding='utf8') as f:
        for key, val in googleresultdict.items():
            f.write(key+'\t'+val+'\n')
            
if __name__ == "__main__":
    main()