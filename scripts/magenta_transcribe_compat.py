import sys

import librosa
import tf_keras.src.legacy_tf_layers as legacy_tf_layers


_original_melspectrogram = librosa.feature.melspectrogram


def _compatible_melspectrogram(*args, **kwargs):
    if args:
        kwargs.setdefault("y", args[0])

    if len(args) > 1:
        kwargs.setdefault("sr", args[1])

    if len(args) > 2:
        raise TypeError("Unsupported positional arguments for melspectrogram")

    return _original_melspectrogram(**kwargs)


librosa.feature.melspectrogram = _compatible_melspectrogram
sys.modules.setdefault("tf_keras.legacy_tf_layers", legacy_tf_layers)

from magenta.models.onsets_frames_transcription.onsets_frames_transcription_transcribe import (  # noqa: E402
    console_entry_point,
)


if __name__ == "__main__":
    sys.exit(console_entry_point())
