/// Local Whisper model management is not available in this app.
///
/// Voice transcription is handled by Android's speech service through
/// [VoiceRecorder], so model downloads, checksums, and storage are not used.
const bool whisperModelManagementSupported = false;
