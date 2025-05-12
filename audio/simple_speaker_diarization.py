# audio/simple_speaker_diarization.py
import numpy as np
import webrtcvad
import soundfile as sf
from sklearn.cluster import KMeans
from scipy.signal import medfilt
import librosa
from config import settings


class SimpleSpeakerDiarizer:
    def __init__(self, n_speakers=None):
        self.vad = webrtcvad.Vad(settings.VAD_AGGRESSIVENESS)
        # Default to None for auto-detection but improved algorithm
        self.n_speakers = n_speakers
        self.frame_duration = 30  # ms
        self.sample_rate = 16000
        self.min_cluster_size = 3  # Mindestanzahl von Segmenten pro Cluster

    def process_audio(self, audio_file_path):
        """Führt eine verbesserte Speaker Diarization durch"""
        # Audio laden und auf 16kHz resamplen
        waveform, original_sr = sf.read(audio_file_path)
        if original_sr != self.sample_rate:
            waveform = librosa.resample(waveform, orig_sr=original_sr, target_sr=self.sample_rate)

        # Mono konvertieren falls nötig
        if len(waveform.shape) > 1:
            waveform = np.mean(waveform, axis=1)

        # Voice Activity Detection
        speech_segments = self._detect_speech(waveform)

        # Features extrahieren für Sprecher-Segmente
        features = self._extract_features(waveform, speech_segments)

        # Clustering der Sprecher
        speaker_labels = self._cluster_speakers(features)

        # Segmente erstellen
        segments = self._create_segments(speech_segments, speaker_labels)

        # Post-Processing: Minimiere kurze Sprecherwechsel
        segments = self._smooth_speaker_transitions(segments)

        return segments

    def _detect_speech(self, waveform):
        """Erkennt Sprachsegmente mit WebRTC VAD"""
        speech_segments = []
        frame_length = int(self.sample_rate * self.frame_duration / 1000)

        for i in range(0, len(waveform) - frame_length, frame_length):
            frame = waveform[i:i + frame_length]
            # PCM16 konvertieren
            frame_pcm = (frame * 32767).astype(np.int16)
            is_speech = self.vad.is_speech(frame_pcm.tobytes(), self.sample_rate)

            if is_speech:
                start_time = i / self.sample_rate
                end_time = (i + frame_length) / self.sample_rate
                speech_segments.append((start_time, end_time))

        # Segmente zusammenführen
        merged_segments = self._merge_segments(speech_segments)
        return merged_segments

    def _merge_segments(self, segments, gap_threshold=0.3):
        """Fügt nahe beieinander liegende Segmente zusammen"""
        if not segments:
            return []

        merged = []
        current_start, current_end = segments[0]

        for start, end in segments[1:]:
            if start - current_end < gap_threshold:
                current_end = end
            else:
                if current_end - current_start >= settings.MIN_SPEECH_DURATION:
                    merged.append((current_start, current_end))
                current_start, current_end = start, end

        if current_end - current_start >= settings.MIN_SPEECH_DURATION:
            merged.append((current_start, current_end))
        return merged

    def _extract_features(self, waveform, segments):
        """Extrahiert erweiterte Audio-Features für bessere Sprechererkennung"""
        features = []

        for start, end in segments:
            start_sample = int(start * self.sample_rate)
            end_sample = int(end * self.sample_rate)
            segment = waveform[start_sample:end_sample]

            # MFCC Features (erweitert)
            mfccs = librosa.feature.mfcc(y=segment, sr=self.sample_rate, n_mfcc=20)  # Erhöht von 13 auf 20
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)  # Standardabweichung hinzugefügt

            # Delta und Delta-Delta (Dynamik-Features)
            mfcc_delta = librosa.feature.delta(mfccs)
            mfcc_delta2 = librosa.feature.delta(mfccs, order=2)
            delta_mean = np.mean(mfcc_delta, axis=1)
            delta2_mean = np.mean(mfcc_delta2, axis=1)

            # Zusätzliche Features
            zcr = np.mean(librosa.feature.zero_crossing_rate(segment))
            rms = np.mean(librosa.feature.rms(y=segment))

            # Spektrale Features hinzufügen
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=segment, sr=self.sample_rate))
            spectral_bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=segment, sr=self.sample_rate))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=segment, sr=self.sample_rate))

            # Fundamental frequency (Pitch) schätzen
            pitches, magnitudes = librosa.piptrack(y=segment, sr=self.sample_rate)
            pitch = 0
            if np.any(magnitudes > 0):
                pitch_idx = np.argmax(magnitudes, axis=0)
                pitches_per_frame = np.take_along_axis(pitches, pitch_idx[np.newaxis, :], axis=0)
                pitch = np.mean(pitches_per_frame[pitches_per_frame > 0]) if np.any(pitches_per_frame > 0) else 0

            # Alle Features kombinieren
            feature_vector = np.concatenate([
                mfcc_mean, mfcc_std, delta_mean, delta2_mean,
                [zcr, rms, spectral_centroid, spectral_bandwidth, spectral_rolloff, pitch]
            ])

            features.append(feature_vector)

        return np.array(features)

    def _cluster_speakers(self, features):
        """Verbesserte Methode zum Clustern von Sprecher-Features"""
        if len(features) < 2:
            return np.zeros(len(features), dtype=int)

        # Standardisiere Features für besseres Clustering
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)

        # Bestimme Anzahl der Sprecher
        if self.n_speakers is None:
            # Automatische Erkennung der Sprecher-Anzahl mit verbesserter Methode
            self.n_speakers = self._estimate_n_speakers(features)
            print(f"[DIARIZER] Geschätzte Sprecheranzahl: {self.n_speakers}")

        # Stelle sicher, dass wir mindestens 2 Sprecher haben, wenn mehr als 5 Segmente vorhanden sind
        # aber nicht mehr als settings.MAX_SPEAKERS
        if len(features) >= 5:
            self.n_speakers = max(2, min(self.n_speakers, settings.MAX_SPEAKERS))

        n_clusters = min(self.n_speakers, len(features))

        # Verwende KMeans mit mehreren Neustarts für bessere Ergebnisse
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(scaled_features)

        # Berechne Cluster-Abstände, um zu überprüfen, ob tatsächlich unterschiedliche Sprecher vorliegen
        cluster_centers = kmeans.cluster_centers_
        if len(cluster_centers) > 1:
            from scipy.spatial.distance import euclidean
            distances = []
            for i in range(len(cluster_centers)):
                for j in range(i + 1, len(cluster_centers)):
                    distances.append(euclidean(cluster_centers[i], cluster_centers[j]))

            avg_distance = np.mean(distances)

            # Wenn die Cluster zu nah beieinander liegen (ähnliche Stimmen),
            # reduziere die Anzahl der Sprecher
            threshold = 2.0  # Anpassbarer Schwellenwert
            if avg_distance < threshold:
                print(
                    f"[DIARIZER] Cluster-Abstand zu gering ({avg_distance:.2f} < {threshold}), reduziere Sprecheranzahl")

                if n_clusters > 2:
                    # Versuche mit weniger Clustern
                    kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
                    labels = kmeans.fit_predict(scaled_features)
                else:
                    # Bei nur 2 Clustern, prüfe ob wir wirklich 2 Sprecher haben
                    # oder alle zu einem zusammenfassen sollten
                    if avg_distance < 1.0:
                        print("[DIARIZER] Sprecher zu ähnlich, verwende nur einen Sprecher")
                        return np.zeros(len(features), dtype=int)

        # Prüfe, ob alle Sprecher genügend Segmente haben
        for i in range(n_clusters):
            if np.sum(labels == i) < self.min_cluster_size:
                print(
                    f"[DIARIZER] Cluster {i} hat zu wenige Segmente ({np.sum(labels == i)}), reduziere Sprecheranzahl")
                # Wenn ein Cluster zu klein ist, reduziere die Anzahl der Sprecher
                if n_clusters > 2:
                    kmeans = KMeans(n_clusters=n_clusters - 1, random_state=42, n_init=10)
                    labels = kmeans.fit_predict(scaled_features)
                    # Prüfe erneut rekursiv
                    return self._validate_and_refine_clusters(labels, scaled_features, n_clusters - 1)
                else:
                    # Bei nur 2 Clustern, prüfe ob wir wirklich 2 Sprecher haben
                    if np.sum(labels == 0) < self.min_cluster_size or np.sum(labels == 1) < self.min_cluster_size:
                        print("[DIARIZER] Zu wenig Segmente für zwei Sprecher, verwende nur einen Sprecher")
                        return np.zeros(len(features), dtype=int)

        # Glättung der Labels mit Median-Filter
        if len(labels) > 5:
            labels = medfilt(labels, kernel_size=5)

        return labels

    def _validate_and_refine_clusters(self, labels, features, n_clusters):
        """Validiert die Cluster und verfeinert sie bei Bedarf"""
        for i in range(n_clusters):
            if np.sum(labels == i) < self.min_cluster_size:
                if n_clusters > 2:
                    kmeans = KMeans(n_clusters=n_clusters - 1, random_state=42, n_init=10)
                    labels = kmeans.fit_predict(features)
                    return self._validate_and_refine_clusters(labels, features, n_clusters - 1)
                else:
                    return np.zeros(len(features), dtype=int)
        return labels

    def _estimate_n_speakers(self, features):
        """Verbesserte Schätzung der Anzahl der Sprecher mit Silhouette-Score"""
        from sklearn.metrics import silhouette_score

        min_clusters = 1
        max_clusters = min(settings.MAX_SPEAKERS, len(features) // 3, 5)  # Begrenzen auf max. 5 Sprecher
        max_clusters = max(max_clusters, 2)  # Mindestens 2 Cluster probieren

        if len(features) < 4:  # Zu wenige Daten für verlässliche Schätzung
            return 1

        best_n_clusters = 1
        best_score = -1

        # Standardisiere Features
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)

        # Teste verschiedene Cluster-Anzahlen
        for n_clusters in range(min_clusters, max_clusters + 1):
            if len(features) <= n_clusters:
                continue

            # KMeans mit mehreren Restarts
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(scaled_features)

            # Berechne Silhouette-Score für diese Cluster-Anzahl
            if n_clusters > 1:  # Silhouette-Score braucht mindestens 2 Cluster
                try:
                    score = silhouette_score(scaled_features, labels)
                    print(f"[DIARIZER] Silhouette-Score für {n_clusters} Cluster: {score:.4f}")

                    if score > best_score:
                        best_score = score
                        best_n_clusters = n_clusters
                except:
                    pass  # Fehler beim Silhouette-Score ignorieren

        # Als Fallback, wenn es mit Silhouette nicht funktioniert
        if best_n_clusters == 1 and len(features) >= 10:
            return 2  # Default zu 2 Sprechern bei genügend Segmenten

        return best_n_clusters

    def _create_segments(self, speech_segments, labels):
        """Erstellt finale Sprecher-Segmente"""
        segments = []

        for (start, end), label in zip(speech_segments, labels):
            segments.append({
                'start': start,
                'end': end,
                'speaker': f'SPEAKER_{int(label)}',
                'duration': end - start
            })

        return segments

    def _smooth_speaker_transitions(self, segments, min_duration=1.0):
        """Glättet Sprecherwechsel durch Entfernen kurzer Segmente des gleichen Sprechers"""
        if len(segments) <= 2:
            return segments

        # Nach Start-Zeit sortieren
        sorted_segments = sorted(segments, key=lambda x: x['start'])

        # Benachbarte Segmente des gleichen Sprechers zusammenführen
        i = 0
        while i < len(sorted_segments) - 1:
            current = sorted_segments[i]
            next_seg = sorted_segments[i + 1]

            # Wenn gleicher Sprecher und nicht zu weit entfernt, zusammenführen
            if (current['speaker'] == next_seg['speaker'] and
                    next_seg['start'] - current['end'] < 0.5):  # Max 0.5s Pause

                # Segmente zusammenführen
                current['end'] = next_seg['end']
                current['duration'] = current['end'] - current['start']

                # Nächstes Segment entfernen
                sorted_segments.pop(i + 1)
            else:
                i += 1

        # Sehr kurze Segmente zwischen gleichen Sprechern eliminieren
        if len(sorted_segments) >= 3:
            i = 1
            while i < len(sorted_segments) - 1:
                prev = sorted_segments[i - 1]
                current = sorted_segments[i]
                next_seg = sorted_segments[i + 1]

                # Wenn aktuelles Segment kurz ist und benachbarte Segmente gleichen Sprecher haben
                if (current['duration'] < min_duration and
                        prev['speaker'] == next_seg['speaker'] and
                        prev['speaker'] != current['speaker']):

                    # Aktuelles Segment dem Sprecher der Nachbarsegmente zuweisen
                    current['speaker'] = prev['speaker']

                    # Optional: Benachbarte Segmente zusammenführen
                    if next_seg['start'] - current['end'] < 0.3 and current['end'] - prev['end'] < 0.3:
                        prev['end'] = next_seg['end']
                        prev['duration'] = prev['end'] - prev['start']
                        sorted_segments.pop(i)
                        sorted_segments.pop(i)  # Nächstes Segment auch entfernen
                        continue

                i += 1

        return sorted_segments