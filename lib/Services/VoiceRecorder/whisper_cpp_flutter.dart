/// Public entry point for the app's platform-backed voice transcription.
///
/// Whisper FFI helpers are not included because this app does not ship the
/// required native library or model assets.
library;

export 'audio_utils.dart' show normalizeVoiceTranscript;
export 'models.dart' show VoiceRecorderEvent, VoiceRecorderEventType;
export 'recorder.dart' show VoiceRecorder;
