import os
import shlex
import subprocess
import tempfile
import sys
import shutil

from detection.detector_errors import DetectorBackendError
from detection.basic_pitch_detector import BasicPitchDetector


class MagentaOnsetsFramesDetector(BasicPitchDetector):
    DEFAULT_COMMAND = "onsets_frames_transcription_transcribe"
    DEFAULT_MODEL_DIR = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "assets",
        "magenta_models",
        "maestro_checkpoint",
        "train",
    )

    def detect_notes_with_time(self, file_path: str):
        command = self.resolve_command()

        if not os.path.exists(command[0]) and not shutil.which(command[0]):
            raise DetectorBackendError(
                "Magenta Onsets and Frames is selected, but its transcription "
                f"command was not found: {command[0]}. Install Magenta Onsets "
                "and Frames or set NAVATUNE_MAGENTA_COMMAND to the CLI command."
            )

        model_dir = os.environ.get(
            "NAVATUNE_MAGENTA_MODEL_DIR",
            self.DEFAULT_MODEL_DIR,
        )

        if not model_dir:
            raise DetectorBackendError(
                "Magenta Onsets and Frames needs a trained checkpoint. Set "
                "NAVATUNE_MAGENTA_MODEL_DIR to the checkpoint/model directory."
            )

        if not os.path.isdir(os.path.expanduser(model_dir)):
            raise DetectorBackendError(
                "NAVATUNE_MAGENTA_MODEL_DIR does not point to an existing "
                f"directory: {model_dir}"
            )

        output_dir = tempfile.mkdtemp(prefix="navatune_magenta_")
        audio_path = os.path.join(output_dir, os.path.basename(file_path))
        shutil.copy2(file_path, audio_path)

        try:
            subprocess.run(
                command
                + [
                    "--model_dir",
                    os.path.expanduser(model_dir),
                    "--load_audio_with_librosa",
                    audio_path,
                ],
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise DetectorBackendError(
                "Magenta Onsets and Frames failed while transcribing this audio."
            ) from error

        return self.detect_notes_from_midi_output(output_dir)

    def resolve_command(self):
        configured_command = os.environ.get("NAVATUNE_MAGENTA_COMMAND")

        if configured_command:
            return shlex.split(configured_command)

        compat_runner = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scripts",
            "magenta_transcribe_compat.py",
        )

        if os.path.exists(compat_runner):
            return [sys.executable, compat_runner]

        return [self.DEFAULT_COMMAND]
