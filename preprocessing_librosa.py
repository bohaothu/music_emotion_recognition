import librosa
import os
import pandas as pd
import csv

class AudioDataSet:

    def __init__(self, load_training_data=False, s_frequency=44100, threshold=2, directory='data/audio_pt4'):
        self.s_frequency = s_frequency
        self.threshold = threshold
        self.directory = directory
        self.annotations = pd.DataFrame()
        self.song_features = pd.DataFrame()
        self.dataset = pd.DataFrame()
        if load_training_data:
            if os.path.exists('data/annotations.csv'):
                self.annotations = pd.read_csv('data/annotations.csv')
            else:
                self.annotations = self.load_audio_anotations()
            if os.path.exists('data/features.csv'):
                self.song_features = pd.read_csv('data/features.csv')
            else:
                if not os.path.exists('data/features_1.csv'):
                    self.song_features = self.load_audio_files()
                self.song_features = self.combine_audio_features_dataframes()
            if os.path.exists('data/dataset.csv'):
                self.dataset = pd.read_csv('data/dataset.csv')
            else:
                self.dataset = self.combine_features_anotations()

            self.x = self.dataset.drop('song_name', axis=1)
            self.x = self.x.drop('valence', axis=1)
            self.x = self.x.drop('arousal', axis=1)
            self.valence = self.dataset.valence
            self.arousal = self.dataset.arousal
        #else:
            # todo call methods for preparing unlabeled data


    def load_audio_anotations(self):
        print("Loading audio annotations")
        v_anotations = pd.read_csv('data/annotations/valence.csv')
        v_anotations = v_anotations.dropna(axis='columns')
        a_anotations = pd.read_csv('data/annotations/arousal.csv')
        a_anotations = a_anotations.dropna(axis='columns')
        # get valence anotations for fragments
        song_names = []
        valence_values = []
        for index, row in v_anotations.iterrows():
            start_time = 15000
            columns_grouped_total = (self.threshold * 1000)/500
            column_sum = 0
            current_columns_grouped = 0
            current_fragment = 1
            while start_time <= 44500:
                column_sum += row[f'sample_{start_time}ms']
                current_columns_grouped += 1
                start_time += 500
                if current_columns_grouped == columns_grouped_total:
                    song_names.append(f'{int(row.song_id)}-{current_fragment}')
                    valence_values.append(column_sum/columns_grouped_total) # average, can be changed for max/min
                    column_sum = 0
                    current_columns_grouped = 0
                    current_fragment += 1
        # get arousal anotations for fragments
        arousal_values = []
        for index, row in a_anotations.iterrows():
            start_time = 15000
            columns_grouped_total = (self.threshold * 1000) / 500
            column_sum = 0
            current_columns_grouped = 0
            while start_time <= 44500:
                column_sum += row[f'sample_{start_time}ms']
                current_columns_grouped += 1
                start_time += 500
                if current_columns_grouped == columns_grouped_total:
                    arousal_values.append(column_sum / columns_grouped_total)  # average, can be changed for max/min
                    column_sum = 0
                    current_columns_grouped = 0
        valence_fragments = pd.DataFrame({'song_name': song_names, 'valence': valence_values, 'arousal': arousal_values})
        valence_fragments.to_csv('data/annotations.csv',  index=False)
        return valence_fragments


    def load_audio_files(self):
        print('Loading audio features')
        songs = {}
        header = 'song_name rmse zero_crossing_rate spectral_centroid spectral_bandwidth rolloff'
        for i in range(1, 21):
            header += f' mfcc{i}'
        header = header.split()
        output_file_name = 'features.csv'
        if os.path.exists(f'data/{output_file_name}'):
            os.remove(f'data/{output_file_name}')
        file = open(f'data/{output_file_name}', 'w', newline='')
        with file:
            writer = csv.writer(file)
            writer.writerow(header)
        cont = 0
        for file_name in os.listdir(self.directory):
            print(f"Progress: filename: {file_name}")
            song_name = f'{self.directory}/{file_name}'
            song, sr = librosa.load(song_name, sr=self.s_frequency)
            start = 15 * self.s_frequency  # annotations start from second 15
            fragment_number = 1
            step = self.threshold * self.s_frequency
            while (start + step < len(song)):
                fragment = song[start:(start + step)]
                fragment_name = f"{file_name.replace('.mp3', '')}-{fragment_number}"
                songs[fragment_name] = fragment
                start += step
                fragment_number += 1
                #get features
                features = self.get_audio_features(fragment)
                to_append = f'{fragment_name}'
                for feature in features:
                    if isinstance(feature, list):
                        for sub_feature in feature:
                            to_append += f' {sub_feature}'
                    else:
                        to_append += f' {feature}'
                file = open(f'data/{output_file_name}', 'a', newline='')
                with file:
                    writer = csv.writer(file)
                    writer.writerow(to_append.split())
            print(f"Progress: processed song# {cont} filename: {file_name}")
            cont += 1
            #if len(songs) > 16:
                #break
        features = pd.read_csv(f'data/{output_file_name}')
        return features

    def get_audio_features(self, song):
        features = []
        rmse = librosa.feature.rmse(song, frame_length=self.s_frequency * self.threshold + 1,
                                    hop_length=self.s_frequency * self.threshold + 1)
        features.append(rmse[0][0])
        zcr = librosa.feature.zero_crossing_rate(song, frame_length=self.s_frequency * self.threshold + 1,
                                                 hop_length=self.s_frequency * self.threshold + 1)
        features.append(zcr[0][0])
        spec_cent = librosa.feature.spectral_centroid(y=song, sr=self.s_frequency,
                                                      hop_length=self.s_frequency * self.threshold + 1)
        features.append(spec_cent[0][0])
        spec_bw = librosa.feature.spectral_bandwidth(y=song, sr=self.s_frequency,
                                                     hop_length=self.s_frequency * self.threshold + 1)
        features.append(spec_bw[0][0])
        rolloff = librosa.feature.spectral_rolloff(y=song, sr=self.s_frequency,
                                                   hop_length=self.s_frequency * self.threshold + 1)
        features.append(rolloff[0][0])
        mfcc = librosa.feature.mfcc(y=song, sr=self.s_frequency,
                                    hop_length=self.s_frequency * self.threshold + 1)
        coefficients = []
        for coefficient in mfcc:
            coefficients.append(coefficient[0])
        features.append(coefficients)
        return features

    def combine_features_anotations(self):
        print('Creating dataset by combining features and annotations')
        dataset = self.song_features.merge(self.annotations, how='inner', on='song_name')
        dataset.to_csv('data/dataset.csv',  index=False)
        return dataset

    def combine_audio_features_dataframes(self):
        print('Combining feature dataframes')
        df1 = pd.read_csv('data/features_1.csv')
        df2 = pd.read_csv('data/features_2.csv')
        df3 = pd.read_csv('data/features_3.csv')
        df4 = pd.read_csv('data/features_4.csv')
        combined_df = pd.concat([df1, df2, df3, df4])
        combined_df.to_csv('data/features.csv', index=False)
        return combined_df



#get duration of song in milliseconds
#from mutagen.mp3 import MP3
#audio = MP3("MEMD_audio/2.mp3")
#print(audio.info.length * 44100)

#show amplitude/time graph
#import matplotlib.pyplot as plt
#import librosa.display
#plt.figure(figsize=(14, 5))
#librosa.display.waveplot(x, sr=sr)
#plt.show()

#show spectogram
#X = librosa.stft(x)
#Xdb = librosa.amplitude_to_db(abs(X))
#plt.figure(figsize=(14, 5))
#librosa.display.specshow(Xdb, sr=sr, x_axis='time', y_axis='hz')
#plt.colorbar()
#plt.show()
